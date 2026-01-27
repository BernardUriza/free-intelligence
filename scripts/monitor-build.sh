#!/bin/bash
# Monitor build and auto-download when complete

BUILD_ID="${1:-21192021808}"
DOWNLOAD_DIR="${2:-$HOME/Downloads}"

echo "🔍 Monitoring build $BUILD_ID..."
echo "📂 Will download to: $DOWNLOAD_DIR"
echo ""

while true; do
    # Get build status
    STATUS=$(gh run view "$BUILD_ID" --json status,conclusion,jobs --jq '{status, conclusion, jobs: [.jobs[] | select(.name == "build-windows") | {name, status, conclusion}]}')

    BUILD_STATUS=$(echo "$STATUS" | jq -r '.status')
    BUILD_CONCLUSION=$(echo "$STATUS" | jq -r '.conclusion')
    WINDOWS_JOB=$(echo "$STATUS" | jq -r '.jobs[0]')
    WINDOWS_STATUS=$(echo "$WINDOWS_JOB" | jq -r '.status')
    WINDOWS_CONCLUSION=$(echo "$WINDOWS_JOB" | jq -r '.status')

    echo "[$(date '+%H:%M:%S')] Build: $BUILD_STATUS | Windows Job: $WINDOWS_STATUS"

    # Check if build-windows completed
    if [[ "$WINDOWS_STATUS" == "completed" ]]; then
        echo ""
        echo "✅ Build Windows job completed!"
        echo "Conclusion: $WINDOWS_CONCLUSION"

        if [[ "$WINDOWS_CONCLUSION" == "success" ]]; then
            echo ""
            echo "🎉 SUCCESS! Downloading artifacts..."

            # Download artifact
            gh run download "$BUILD_ID" --name aurity-windows-nsis --dir "$DOWNLOAD_DIR"

            if [[ $? -eq 0 ]]; then
                echo ""
                echo "✅ Downloaded to: $DOWNLOAD_DIR"

                # Show file info
                EXE_FILE=$(find "$DOWNLOAD_DIR" -name "Aurity*.exe" -type f | head -1)
                if [[ -n "$EXE_FILE" ]]; then
                    echo ""
                    echo "📦 File: $(basename "$EXE_FILE")"
                    echo "📏 Size: $(du -h "$EXE_FILE" | cut -f1)"
                    echo "🔐 SHA256: $(shasum -a 256 "$EXE_FILE" | cut -d' ' -f1)"
                fi
            else
                echo "❌ Download failed"
                exit 1
            fi

            exit 0
        else
            echo "❌ Build failed with conclusion: $WINDOWS_CONCLUSION"
            echo ""
            echo "View logs:"
            echo "  gh run view $BUILD_ID --log-failed"
            exit 1
        fi
    fi

    # Wait before next check
    sleep 30
done
