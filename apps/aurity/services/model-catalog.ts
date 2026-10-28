import type { ModelCatalogStore } from 'fi-glass/model-catalog';
import {
  createLLMModel,
  deleteLLMModel,
  fetchLLMModels,
  testLLMModel,
  updateLLMModel,
} from '@aurity-standalone/api-client/llm-models';
import { deleteInstalledModel, fetchCatalogModels, installModelWithProgress } from '@/lib/api/catalog';
import { fetchRunningModels, fetchSystemResources, unloadModel } from '@/lib/api/system';

export const modelCatalogStore: ModelCatalogStore = {
  listModels: (filter) => fetchLLMModels(filter),
  createModel: createLLMModel,
  updateModel: updateLLMModel,
  deactivateModel: (modelId) => deleteLLMModel(modelId),
  testModel: testLLMModel,
  listCatalog: async ({ source, query, maxSizeGb, signal }) =>
    (await fetchCatalogModels({ source, query, max_size_gb: maxSizeGb, signal })).models,
  installCatalogModel: (modelId, options) => installModelWithProgress(modelId, options),
  removeCatalogModel: deleteInstalledModel,
  getSystemResources: fetchSystemResources,
  listRunningModels: fetchRunningModels,
  unloadRunningModel: unloadModel,
};
