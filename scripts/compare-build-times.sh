#!/bin/bash
# Compara tiempos de build entre 2 runs

OLD_BUILD=${1:-21175698415}
NEW_BUILD=${2:-21176219299}

echo "📊 Comparación de Build Times"
echo "=============================="
echo ""

for BUILD in $OLD_BUILD $NEW_BUILD; do
  echo "Build #$BUILD:"

  TIMING=$(gh run view $BUILD --json jobs 2>/dev/null | jq -r '
    .jobs[] |
    select(.name == "build-windows") |
    {
      started: .startedAt,
      completed: .completedAt,
      status: .status,
      conclusion: .conclusion
    }
  ')

  STATUS=$(echo "$TIMING" | jq -r '.status')

  if [ "$STATUS" = "completed" ]; then
    STARTED=$(echo "$TIMING" | jq -r '.startedAt')
    COMPLETED=$(echo "$TIMING" | jq -r '.completedAt')

    # Calculate duration in seconds
    START_SEC=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$STARTED" "+%s" 2>/dev/null || echo "0")
    END_SEC=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$COMPLETED" "+%s" 2>/dev/null || echo "0")

    if [ "$START_SEC" != "0" ] && [ "$END_SEC" != "0" ]; then
      DURATION=$((END_SEC - START_SEC))
      MINUTES=$((DURATION / 60))
      SECONDS=$((DURATION % 60))

      CONCLUSION=$(echo "$TIMING" | jq -r '.conclusion')

      echo "  ⏱️  Tiempo: ${MINUTES}m ${SECONDS}s"
      echo "  📊 Status: $CONCLUSION"
    else
      echo "  ⚠️  No se pudo calcular duración"
    fi
  else
    echo "  🔄 Status: $STATUS (aún no termina)"
  fi

  echo ""
done

echo "=============================="
