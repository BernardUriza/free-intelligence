#!/bin/bash
# Fix all obsolete imports from backend.src.fi_* to new structure

set -e

echo "Fixing obsolete imports..."

# fi_common.logging.logger -> utils.common.logging.logger
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.logging\.logger/from backend.utils.common.logging.logger/g' {} +

# fi_common.config.config_loader -> utils.common.config.config_loader
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.config\.config_loader/from backend.utils.common.config.config_loader/g' {} +

# fi_common.config.deployment -> utils.common.config.deployment
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.config\.deployment/from backend.utils.common.config.deployment/g' {} +

# fi_common.infrastructure.container -> utils.common.infrastructure.container
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.infrastructure\.container/from backend.utils.common.infrastructure.container/g' {} +

# fi_common.logger -> utils.common.logging.logger
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.logger/from backend.utils.common.logging.logger/g' {} +

# fi_common.cache.cache -> utils.common.cache.cache
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.cache\.cache/from backend.utils.common.cache.cache/g' {} +

# fi_common.metrics.metrics -> utils.common.metrics.metrics
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.metrics\.metrics/from backend.utils.common.metrics.metrics/g' {} +

# fi_common.security.validator -> utils.common.security.validator
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.security\.validator/from backend.utils.common.security.validator/g' {} +

# fi_common.infrastructure.evidence_pack -> utils.common.infrastructure.evidence_pack
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.infrastructure\.evidence_pack/from backend.utils.common.infrastructure.evidence_pack/g' {} +

# fi_common.types.type_defs -> utils.common.types.type_defs
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.types\.type_defs/from backend.utils.common.types.type_defs/g' {} +

# fi_common.services.export_service -> utils.common.services.export_service
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_common\.services\.export_service/from backend.utils.common.services.export_service/g' {} +

# fi_storage.infrastructure.hdf5 -> core.infrastructure.storage.infrastructure.hdf5
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_storage\.infrastructure\.hdf5/from backend.core.infrastructure.storage.infrastructure.hdf5/g' {} +

# fi_storage.services.corpus_service -> core.infrastructure.storage.services.corpus_service
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_storage\.services\.corpus_service/from backend.core.infrastructure.storage.services.corpus_service/g' {} +

# fi_llm.services -> core.services.llm.services
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_llm\.services/from backend.core.services.llm.services/g' {} +
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_llm import services/from backend.core.services.llm import services/g' {} +

# fi_model_catalog.services -> core.infrastructure.model_catalog.services
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_model_catalog\.services/from backend.core.infrastructure.model_catalog.services/g' {} +

# fi_soap_generation.services -> core.services.soap.services
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_soap_generation\.services/from backend.core.services.soap.services/g' {} +

# fi_transcription.services -> core.services.transcription.services
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_transcription\.services/from backend.core.services.transcription.services/g' {} +

# fi_tts.services -> core.services.tts.services
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_tts\.services/from backend.core.services.tts.services/g' {} +

# fi_kpi.services -> core.services.kpi.services
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_kpi\.services/from backend.core.services.kpi.services/g' {} +

# fi_audit.services -> api.audit.services
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_audit\.services/from backend.api.audit.services/g' {} +

# fi_workers.tasks -> core.infrastructure.workers.tasks
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_workers\.tasks/from backend.core.infrastructure.workers.tasks/g' {} +

# fi_workflow -> core.services.workflow
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_workflow\.api\.public/from backend.core.services.workflow.api.public/g' {} +
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_workflow\.services/from backend.core.services.workflow.services/g' {} +

# fi_memory.api.public -> core.services.memory.api.public
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_memory\.api\.public/from backend.core.services.memory.api.public/g' {} +

# fi_session.api.public -> core.domain.session.api.public
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_session\.api\.public/from backend.core.domain.session.api.public/g' {} +

# fi_assistant.api.public -> core.services.assistant.api.public
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_assistant\.api\.public/from backend.core.services.assistant.api.public/g' {} +

# fi_coder -> utils.coder
find backend/ -name "*.py" -type f -exec sed -i '' 's/from backend\.src\.fi_coder/from backend.utils.coder/g' {} +

echo "✅ Imports fixed. Verifying..."

# Count remaining obsolete imports
remaining=$(grep -r "from backend\.src\." backend/ --include="*.py" | wc -l | tr -d ' ')

if [ "$remaining" -eq "0" ]; then
    echo "✅ All imports fixed! No obsolete imports remain."
else
    echo "⚠️  $remaining obsolete imports still remain:"
    grep -r "from backend\.src\." backend/ --include="*.py" | head -20
    exit 1
fi
