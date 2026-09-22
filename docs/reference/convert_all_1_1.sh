#!/usr/bin/env bash

set -euo pipefail

# Dependencies check
for cmd in magick exiftool ffmpeg ffprobe awk stat; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: Required command '$cmd' is not installed." >&2
        exit 1
    fi
done

# ==========================================
# VIDEO ENCODER SETUP & HELPERS
# ==========================================
detect_encoder() {
    local encoders
    encoders=$(ffmpeg -encoders 2>/dev/null)

    if echo "$encoders" | grep -q "av1_nvenc"; then
        echo "nvenc"
    elif echo "$encoders" | grep -q "av1_qsv"; then
        echo "qsv"
    elif echo "$encoders" | grep -q "av1_vaapi" && [ -e /dev/dri/renderD128 ]; then
        echo "vaapi"
    else
        echo "svt"
    fi
}

HW_TYPE=$(detect_encoder)
echo "Detected AV1 encoder mode: $HW_TYPE"

is_browser_compatible() {
    local file="$1"
    local ext="${file##*.}"
    ext="${ext,,}"

    if [[ "$ext" != "mp4" && "$ext" != "webm" && "$ext" != "mov" ]]; then
        return 1
    fi

    local v_codec a_codec
    v_codec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null || true)
    a_codec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null || true)

    case "$v_codec" in
        h264|hevc|vp9|av1) ;;
        *) return 1 ;;
    esac

    if [[ -n "$a_codec" ]]; then
        case "$a_codec" in
            aac|mp3|opus|vorbis|flac) ;;
            *) return 1 ;;
        esac
    fi

    return 0
}

get_bitrate_bps() {
    local file="$1"
    local bitrate
    bitrate=$(ffprobe -v error -show_entries format=bit_rate -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null || echo "")

    if [[ "$bitrate" =~ ^[0-9]+$ ]] && (( bitrate > 0 )); then
        echo "$bitrate"
        return
    fi

    local orig_size duration
    orig_size=$(stat -c%s "$file" 2>/dev/null || echo 0)
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null || echo 0)

    if [[ "$orig_size" -gt 0 && -n "$duration" ]]; then
        awk -v s="$orig_size" -v d="$duration" 'BEGIN { if (d > 0) print int((s * 8) / d); else print 0 }'
    else
        echo 0
    fi
}

# ==========================================
# CONVERSION FUNCTIONS
# ==========================================

convert_to_avif() {
    local input="$1"
    local ext="${input##*.}"
    local ext_lower="${ext,,}"
    local base="${input%.*}"
    local output="${base}.avif"
    local tmp_jpg="${base}.tmp.jpg"

    if [[ "$ext_lower" == "avif" ]]; then
        return 0
    fi

    # ==========================================
    # COLLISION & CLEANUP LOGIC (IMAGES)
    # ==========================================
    local is_collision=false

    # Check if the base AVIF file already exists
    if [[ -f "$output" ]]; then
        # If the input is a JPEG, we assume this is a RAW+JPEG scenario where the RAW was already converted.
        # We trigger collision handling to give this JPEG its own AVIF file.
        if [[ "$ext_lower" == "jpg" || "$ext_lower" == "jpeg" ]]; then
            is_collision=true
            output="${base}_${ext}.avif"
            echo "[INFO] Base AVIF exists. Avoiding overwrite for JPG by targeting: $output"
        else
            # For everything else (PNG, TIFF, RAW, etc.), if the AVIF exists we assume it's the converted version.
            # We strictly validate the AVIF, and if good, clean up the forgotten original file.
            if [[ -s "$output" ]] && magick identify "$output" >/dev/null 2>&1; then
                echo "[CLEANUP] Valid AVIF already exists for $input. Deleting original file safely."
                rm -f "$input"
                return 0
            else
                echo "[WARNING] $output exists but is empty or invalid. Re-converting..."
            fi
        fi
    fi

    # If we are in collision mode (JPG), check if the secondary AVIF already exists for cleanup
    if [[ "$is_collision" == true && -f "$output" ]]; then
        if [[ -s "$output" ]] && magick identify "$output" >/dev/null 2>&1; then
            echo "[CLEANUP] Valid collision AVIF ($output) already exists. Deleting original JPG safely."
            rm -f "$input"
            return 0
        else
            echo "[WARNING] $output exists but is empty or invalid. Re-converting..."
        fi
    fi

    echo "======================================"
    echo "Processing Image: $input"

    # Attempt primary conversion
    if ! magick "$input" \
        -depth 10 \
        -quality 80 \
        -define avif:chroma-subsampling=444 \
        "$output" 2>/dev/null; then

        # FALLBACK FOR STUBBORN RAW FILES
        if [[ "$ext_lower" =~ ^(dng|cr2|cr3|nef|nrw|arw|srf|sr2|raf|orf|rw2|pef|srw)$ ]]; then
            echo "[WARNING] ImageMagick failed to read RAW file ($ext_lower). Attempting to extract embedded full-res preview..."

            # Extract the embedded PreviewImage or JpgFromRaw using ExifTool
            exiftool -b -PreviewImage "$input" > "$tmp_jpg" 2>/dev/null || true
            if [[ ! -s "$tmp_jpg" ]]; then
                exiftool -b -JpgFromRaw "$input" > "$tmp_jpg" 2>/dev/null || true
            fi

            # If we successfully extracted an image, convert it to AVIF
            if [[ -s "$tmp_jpg" ]]; then
                if magick "$tmp_jpg" -depth 10 -quality 80 -define avif:chroma-subsampling=444 "$output"; then
                    echo "[INFO] Successfully converted extracted preview to AVIF."
                else
                    echo "[ERROR] Failed to convert extracted preview."
                    rm -f "$output"
                fi
                rm -f "$tmp_jpg" # Clean up temporary file
            else
                echo "[ERROR] Could not extract embedded image from RAW file. Skipping file."
                rm -f "$output" "$tmp_jpg" 2>/dev/null
                return 0
            fi
        else
            echo "[ERROR] ImageMagick failed to process this file. Skipping safely."
            rm -f "$output" 2>/dev/null
            return 0
        fi
    fi

    exiftool -overwrite_original -TagsFromFile "$input" -all:all "$output" &>/dev/null || true

    # FAST VALIDATION & CLEANUP
    if [[ -s "$output" ]] && magick identify "$output" >/dev/null 2>&1; then
        echo "[SUCCESS] Valid AVIF created. Deleting original image."
        rm -f "$input"
    else
        echo "[ERROR] Validation failed or output is empty. Keeping original."
    fi
}

convert_to_av1() {
    local input="$1"
    local output="${input%.*}.av1.mp4"

    # Make it case insensitive so .AV1.MP4 is also skipped
    if [[ "${input,,}" == *.av1.mp4 ]]; then
        return 0
    fi

    # ==========================================
    # CLEANUP LOGIC FOR FORGOTTEN VIDEOS
    # ==========================================
    if [[ -f "$output" ]]; then
        # Strictly validate the existing AV1 file
        if [[ -s "$output" ]] && ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$output" >/dev/null 2>&1; then
            echo "[CLEANUP] Valid AV1 video already exists for $input. Deleting original file safely."
            rm -f "$input"
            return 0
        else
            echo "[WARNING] $output exists but is empty or invalid. Re-converting..."
        fi
    fi

    local current_v_codec
    current_v_codec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$input" 2>/dev/null || true)
    if [[ "${current_v_codec,,}" == "av1" ]]; then
        echo "Skipping (Video stream is already AV1): $input"
        return 0
    fi

    if is_browser_compatible "$input"; then
        local bps
        bps=$(get_bitrate_bps "$input")
        if [[ "$bps" -gt 0 ]] && (( bps <= 1500000 )); then
            echo "Skipping (already web-compatible & low bitrate): $input"
            return 0
        fi
    fi

    echo "======================================"
    echo "Processing Video: $input"

    local encode_status=0

    case "$HW_TYPE" in
        nvenc)
            ffmpeg -nostdin -hide_banner -loglevel error -stats -i "$input" \
                -map 0:v:0 -map 0:a? \
                -c:v av1_nvenc -preset p6 -cq 24 -pix_fmt p010le \
                -c:a libopus -b:a 256k \
                -map_metadata 0 \
                -movflags +faststart \
                "$output" || encode_status=$?
            ;;
        qsv)
            ffmpeg -nostdin -hide_banner -loglevel error -stats -i "$input" \
                -map 0:v:0 -map 0:a? \
                -c:v av1_qsv -global_quality 24 -preset medium -pix_fmt p010le \
                -c:a libopus -b:a 256k \
                -map_metadata 0 \
                -movflags +faststart \
                "$output" || encode_status=$?
            ;;
        vaapi)
            ffmpeg -nostdin -hide_banner -loglevel error -stats \
                -vaapi_device /dev/dri/renderD128 -i "$input" \
                -map 0:v:0 -map 0:a? \
                -vf 'format=p010,hwupload' \
                -c:v av1_vaapi -rc_mode CQP -qp 24 \
                -c:a libopus -b:a 256k \
                -map_metadata 0 \
                -movflags +faststart \
                "$output" || encode_status=$?
            ;;
        *)
            ffmpeg -nostdin -hide_banner -loglevel error -stats -i "$input" \
                -map 0:v:0 -map 0:a? \
                -c:v libsvtav1 -crf 23 -preset 5 -pix_fmt yuv420p10le \
                -c:a libopus -b:a 256k \
                -map_metadata 0 \
                -movflags +faststart \
                "$output" || encode_status=$?
            ;;
    esac

    if (( encode_status != 0 )); then
        echo "[ERROR] FFmpeg encountered an error processing this video. Skipping safely."
        rm -f "$output" 2>/dev/null
        return 0
    fi

    local orig_size output_size max_allowed_size
    orig_size=$(stat -c%s "$input")
    output_size=$(stat -c%s "$output" 2>/dev/null || echo 0)
    max_allowed_size=$(( orig_size + orig_size / 10 ))

    if (( output_size == 0 )); then
        echo "[ERROR] FFmpeg failed to produce an output file. Keeping original."
        rm -f "$output" 2>/dev/null
        return 0
    fi

    if (( output_size > max_allowed_size )); then
        if is_browser_compatible "$input"; then
            echo "[ROLLBACK] Output is >10% larger and source is already web-compatible. Deleting AV1 output. Keeping original."
            rm -f "$output"
            return 0
        else
            echo "[INFO] Output is >10% larger, but source is not web-compatible. Retaining AV1 output."
        fi
    fi

    # FAST VALIDATION & CLEANUP
    if [[ -s "$output" ]] && ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$output" >/dev/null 2>&1; then
        echo "[SUCCESS] Valid AV1 created. Deleting original video."
        rm -f "$input"
    else
        echo "[ERROR] Validation failed for AV1 output. Keeping original."
    fi
}

# ==========================================
# MAIN EXECUTION
# ==========================================

process_file() {
    local file="$1"
    local ext="${file##*.}"
    ext="${ext,,}"

    case "$ext" in
        jpg|jpeg|png|webp|tiff|jxl|heic|heif|dng|avif|cr2|cr3|nef|nrw|arw|srf|sr2|raf|orf|rw2|pef|srw)
            convert_to_avif "$file"
            ;;
        mp4|mov|mkv|webm|avi|m4v|mts|m2ts)
            convert_to_av1 "$file"
            ;;
        *)
            echo "Skipping unsupported format: $file"
            ;;
    esac
}

target="${1:-.}"

if [ -f "$target" ]; then
    process_file "$target"
elif [ -d "$target" ]; then
    find "$target" -type f \( \
        -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o \
        -iname "*.webp" -o -iname "*.tiff" -o -iname "*.jxl" -o \
        -iname "*.heic" -o -iname "*.heif" -o -iname "*.dng" -o \
        -iname "*.cr2" -o -iname "*.cr3" -o -iname "*.nef" -o \
        -iname "*.nrw" -o -iname "*.arw" -o -iname "*.srf" -o \
        -iname "*.sr2" -o -iname "*.raf" -o -iname "*.orf" -o \
        -iname "*.rw2" -o -iname "*.pef" -o -iname "*.srw" -o \
        -iname "*.mp4" -o -iname "*.mov" -o -iname "*.mkv" -o \
        -iname "*.webm" -o -iname "*.avi" -o -iname "*.m4v" -o \
        -iname "*.mts" -o -iname "*.m2ts" \
    \) -print0 | while IFS= read -r -d '' file; do
        process_file "$file"
    done
else
    echo "Error: Target '$target' is not a valid file or directory." >&2
    exit 1
fi

echo "======================================"
echo "All conversions complete!"
