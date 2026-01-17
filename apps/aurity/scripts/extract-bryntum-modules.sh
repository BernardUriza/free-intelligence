#!/bin/bash
# Extract key Bryntum modules based on known line numbers

SRC="public/js/bryntum/schedulerpro.wc.module.js"
OUT="public/js/bryntum/modules"

mkdir -p "$OUT"

echo "Extracting Bryntum modules..."

# Header (first 50 lines - runtime helpers)
sed -n '1,50p' "$SRC" > "$OUT/00-header.js"
echo "  00-header.js (50 lines)"

# DragHelper class (lines 56411-57222)
sed -n '56400,57230p' "$SRC" > "$OUT/30-drag-helper.js"
echo "  30-drag-helper.js (830 lines)"

# DragContext (lines 61076-61662)
sed -n '61070,61670p' "$SRC" > "$OUT/31-drag-context.js"
echo "  31-drag-context.js (600 lines)"

# DragCreateBase (lines 160054-168385)
sed -n '160050,168390p' "$SRC" > "$OUT/33-drag-create-base.js"
echo "  33-drag-create-base.js (8340 lines)"

# EventDragCreate - THE KEY MODULE (lines 168386-168700)
sed -n '168380,168750p' "$SRC" > "$OUT/34-event-drag-create.js"
echo "  34-event-drag-create.js (370 lines) *** KEY MODULE ***"

# EventModel (lines 135416-135550)
sed -n '135410,135560p' "$SRC" > "$OUT/40-event-model.js"
echo "  40-event-model.js (150 lines)"

# EventStore (lines 135552-145000)
sed -n '135550,145100p' "$SRC" > "$OUT/41-event-store.js"
echo "  41-event-store.js (9550 lines)"

# SchedulerBase (lines 155761-160000)
sed -n '155760,160000p' "$SRC" > "$OUT/50-scheduler-base.js"
echo "  50-scheduler-base.js (4240 lines)"

# ResourceTimeRangeModel (lines 122200-122700)
sed -n '122200,122700p' "$SRC" > "$OUT/62-resource-time-range.js"
echo "  62-resource-time-range.js (500 lines)"

echo ""
echo "Done! Key file to edit:"
echo "  $OUT/34-event-drag-create.js"
echo ""
echo "Look for handleBeforeDragCreate method (~line 100 in extracted file)"
