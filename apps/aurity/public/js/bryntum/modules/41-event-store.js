// ../Scheduler/lib/Scheduler/data/EventStore.js
var EngineMixin4 = PartOfProject_default(CoreEventStoreMixin.derive(AjaxStore));
var EventStore = class extends EngineMixin4.mixin(
  RecurringEventsMixin_default,
  EventStoreMixin_default,
  DayIndexMixin_default,
  GetEventsMixin_default,
) {
  static get defaultConfig() {
    return {
      /**
       * Class used to represent records
       * @config {Scheduler.model.EventModel}
       * @typings {typeof EventModel}
       * @default
       * @category Common
       */
      modelClass: EventModel,
    };
  }
};
__publicField(EventStore, "$name", "EventStore");
EventStore._$name = "EventStore";

// ../Scheduler/lib/Scheduler/model/mixin/AssignmentModelMixin.js
var getPath = ObjectHelper.getPath;
var setFieldValue = (data, field2, complexMapping, value) => {
  if (complexMapping) {
    ObjectHelper.setPath(data, field2, value);
  } else {
    data[field2] = value;
  }
};
var setModelField = (data, field2, complexMapping, model) => {
  var _a4;
  if (
    (model == null ? void 0 : model.isModel) &&
    !((_a4 = getPath(data, field2)) == null ? void 0 : _a4.model)
  ) {
    setFieldValue(data, field2, complexMapping, model);
  }
};
var AssignmentModelMixin_default = (Target) =>
  class AssignmentModelMixin extends Target {
    static get $name() {
      return "AssignmentModelMixin";
    }
    /**
     * Set value for the specified field(s), triggering engine calculations immediately. See
     * {@link Core.data.Model#function-set Model#set()} for arguments.
     *
     * ```javascript
     * assignment.set('resourceId', 2);
     * // assignment.resource is not yet resolved
     *
     * await assignment.setAsync('resourceId', 2);
     * // assignment.resource is resolved
     * ```
     *
     * @param {String|Object} field The field to set value for, or an object with multiple values to set in one call
     * @param {*} [value] Value to set
     * @param {Boolean} [silent=false] Set to true to not trigger events
     * automatically.
     * @function setAsync
     * @category Editing
     * @async
     */
    //region Fields
    static get fields() {
      return [
        /**
         * Id for the resource to assign to
         * @field {String|Number} resourceId
         * @category Common
         */
        "resourceId",
        /**
         * Id for the event to assign
         * @field {String|Number} eventId
         * @category Common
         */
        "eventId",
        /**
         * Specify `false` to opt out of drawing dependencies from/to this assignment
         * @field {Boolean} drawDependencies
         * @category Common
         */
        { name: "drawDependencies", type: "boolean" },
        "event",
        "resource",
      ];
    }
    //endregion
    construct(data, ...args) {
      var _a4, _b;
      data = data || {};
      const { fieldMap } = this,
        eventIdField = fieldMap.eventId.dataSource,
        resourceIdField = fieldMap.resourceId.dataSource,
        eventField = fieldMap.event.dataSource,
        resourceField = fieldMap.resource.dataSource,
        eventIdComplexMapping = fieldMap.eventId.complexMapping,
        resourceIdComplexMapping = fieldMap.resourceId.complexMapping,
        eventComplexMapping = fieldMap.event.complexMapping,
        resourceComplexMapping = fieldMap.resource.complexMapping,
        eventId = eventIdComplexMapping
          ? getPath(data, eventIdField)
          : data[eventIdField],
        resourceId = resourceIdComplexMapping
          ? getPath(data, resourceIdField)
          : data[resourceIdField],
        event = ((_a4 = data.event) == null ? void 0 : _a4.isModel)
          ? data.event
          : eventComplexMapping
            ? getPath(data, eventField)
            : data[eventField],
        resource = ((_b = data.resource) == null ? void 0 : _b.isModel)
          ? data.resource
          : resourceComplexMapping
            ? getPath(data, resourceField)
            : data[resourceField];
      if (eventId != null) {
        setFieldValue(data, eventField, eventComplexMapping, eventId);
      } else if (event != null) {
        const value = event.isModel ? event.id : event;
        setFieldValue(data, eventIdField, eventIdComplexMapping, value);
      }
      if (resourceId != null) {
        setFieldValue(data, resourceField, resourceComplexMapping, resourceId);
      } else if (resource != null) {
        const value = resource.isModel ? resource.id : resource;
        setFieldValue(data, resourceIdField, resourceIdComplexMapping, value);
      }
      setModelField(data, eventField, eventComplexMapping, data.event);
      setModelField(data, resourceField, resourceComplexMapping, data.resource);
      super.construct(data, ...args);
    }
    //region Event & resource
    /**
     * A key made up from the event id and the id of the resource assigned to.
     * @property eventResourceKey
     * @readonly
     * @internal
     */
    get eventResourceKey() {
      return this.buildEventResourceKey(this.event, this.resource);
    }
    buildEventResourceKey(event, resource) {
      let eventKey, resourceKey;
      if (event) {
        eventKey = event.isModel ? event.id : event;
      } else {
        eventKey = this.internalId;
      }
      if (resource) {
        resourceKey = resource.isModel ? resource.id : resource;
      } else {
        resourceKey = this.internalId;
      }
      return `${eventKey}-${resourceKey}`;
    }
    buildIndexKey({ event, resource }) {
      return this.buildEventResourceKey(event, resource);
    }
    set(field2, value, ...args) {
      var _a4, _b;
      const toSet = this.fieldToKeys(field2, value);
      if ("resource" in toSet) {
        if (((_a4 = toSet.resource) == null ? void 0 : _a4.id) !== void 0) {
          toSet.resourceId = toSet.resource.id;
        }
      } else if (
        "resourceId" in toSet &&
        this.constructor.isProAssignmentModel
      ) {
        toSet.resource = toSet.resourceId;
      }
      if ("event" in toSet) {
        if (((_b = toSet.event) == null ? void 0 : _b.id) !== void 0) {
          toSet.eventId = toSet.event.id;
        }
      } else if ("eventId" in toSet && this.constructor.isProAssignmentModel) {
        toSet.event = toSet.eventId;
      }
      return super.set(toSet, null, ...args);
    }
    afterChange(toSet, wasSet, silent, fromRelationUpdate, skipAccessors) {
      var _a4, _b;
      const me = this;
      if (
        !me.constructor.isProAssignmentModel &&
        (wasSet == null ? void 0 : wasSet.resourceId) &&
        ((_a4 = me.resource) == null ? void 0 : _a4.id) !==
          wasSet.resourceId.value
      ) {
        me.resource = wasSet.resourceId.value;
      } else if (
        me.constructor.isProAssignmentModel &&
        ((_b = me.project) == null ? void 0 : _b.propagatingSyncChanges) &&
        (wasSet == null ? void 0 : wasSet.eventId) &&
        !(wasSet == null ? void 0 : wasSet.event) &&
        (toSet.event.value === wasSet.eventId.value ||
          toSet.event.value.id === wasSet.eventId.value)
      ) {
        delete wasSet.eventId;
        delete me.meta.modified.eventId;
      }
      return super.afterChange(...arguments);
    }
    // Settings resourceId relays to `resource`. Underlying data will be updated in `afterChange()` above
    set resourceId(value) {
      const { resource } = this;
      if (
        (resource == null ? void 0 : resource.isModel) &&
        resource.id === value
      ) {
        this.set("resourceId", value);
      } else {
        this.resource = value;
      }
    }
    get resourceId() {
      var _a4, _b;
      return (_b = (_a4 = this.resource) == null ? void 0 : _a4.id) != null
        ? _b
        : this.get("resourceId");
    }
    // Same for event as for resourceId
    set eventId(value) {
      const { event } = this;
      if ((event == null ? void 0 : event.isModel) && event.id === value) {
        this.set("eventId", value);
      } else {
        this.event = value;
      }
    }
    get eventId() {
      var _a4, _b;
      return (_b = (_a4 = this.event) == null ? void 0 : _a4.id) != null
        ? _b
        : this.get("eventId");
    }
    /**
     * Convenience property to get the name of the associated event.
     * @property {String}
     * @readonly
     */
    get eventName() {
      var _a4;
      return (_a4 = this.event) == null ? void 0 : _a4.name;
    }
    /**
     * Convenience property to get the name of the associated resource.
     * @property {String}
     * @readonly
     */
    get resourceName() {
      var _a4;
      return (_a4 = this.resource) == null ? void 0 : _a4.name;
    }
    /**
     * Returns the resource associated with this assignment.
     *
     * @returns {Scheduler.model.ResourceModel} Instance of resource
     */
    getResource() {
      return this.resource;
    }
    //endregion
    // Convenience getter to not have to check `instanceof AssignmentModel`
    get isAssignment() {
      return true;
    }
    /**
     * Returns true if the Assignment can be persisted (e.g. task and resource are not 'phantoms')
     *
     * @property {Boolean}
     */
    get isPersistable() {
      var _a4;
      const { event, resource, unjoinedStores, assignmentStore } = this,
        crudManager =
          assignmentStore == null ? void 0 : assignmentStore.crudManager;
      let result;
      if (assignmentStore) {
        result =
          this.isValid &&
          event.isPersistable &&
          (crudManager || (!event.hasGeneratedId && !resource.hasGeneratedId));
      } else {
        result = !this.isPhantom && Boolean(unjoinedStores[0]);
      }
      return (
        result &&
        super.isPersistable &&
        !((_a4 = this.event) == null ? void 0 : _a4.isCreating)
      );
    }
    get isValid() {
      return this.resource != null && this.event != null;
    }
    /**
     * Returns a textual representation of this assignment (e.g. Mike 50%).
     * @returns {String}
     */
    toString() {
      if (this.resourceName) {
        return `${this.resourceName} ${Math.round(this.units)}%`;
      }
      return "";
    }
    //region STM hooks
    shouldRecordFieldChange(fieldName, oldValue, newValue) {
      var _a4, _b;
      if (!super.shouldRecordFieldChange(fieldName, oldValue, newValue)) {
        return false;
      }
      if (fieldName === "event" || fieldName === "eventId") {
        const eventStore =
          (_a4 = this.project) == null ? void 0 : _a4.eventStore;
        if (
          eventStore &&
          eventStore.oldIdMap[oldValue] === eventStore.getById(newValue)
        ) {
          return false;
        }
      }
      if (fieldName === "resource" || fieldName === "resourceId") {
        const resourceStore =
          (_b = this.project) == null ? void 0 : _b.resourceStore;
        if (
          resourceStore &&
          resourceStore.oldIdMap[oldValue] === resourceStore.getById(newValue)
        ) {
          return false;
        }
      }
      return true;
    }
    //endregion
  };

// ../Engine/lib/Engine/quark/model/scheduler_core/CoreAssignmentMixin.js
function asId(recordOrId) {
  return (recordOrId == null ? void 0 : recordOrId.isModel)
    ? recordOrId.id
    : recordOrId;
}
var CoreAssignmentMixin = class extends Mixin(
  [CorePartOfProjectModelMixin],
  (base) => {
    const superProto = base.prototype;
    class CoreAssignmentMixin2 extends base {
      // Fields declared in the Model way, existing decorators all assume ChronoGraph is used
      static get fields() {
        return [
          // isEqual required to properly detect changed resource / event
          { name: "resource", isEqual: (a, b) => a === b, persist: false },
          { name: "event", isEqual: (a, b) => a === b, persist: false },
        ];
      }
      // Resolve early + update indices to have buckets ready before commit
      setChanged(field2, value, invalidate) {
        const { assignmentStore, eventStore, resourceStore, project } = this;
        let update = false;
        if (field2 === "event") {
          const event = isInstanceOf(value, CoreEventMixin)
            ? value
            : eventStore == null
              ? void 0
              : eventStore.$master.getById(value);
          if (event) update = true;
          value = event || value;
        }
        if (field2 === "resource") {
          const resource = isInstanceOf(value, CoreResourceMixin)
            ? value
            : resourceStore == null
              ? void 0
              : resourceStore.$master.getById(value);
          if (resource) update = true;
          value = resource || value;
        }
        superProto.setChanged.call(this, field2, value, invalidate, true);
        if (
          assignmentStore &&
          update &&
          !project.isPerformingCommit &&
          !assignmentStore.isLoadingData &&
          !(resourceStore == null ? void 0 : resourceStore.isLoadingData) &&
          !assignmentStore.skipInvalidateIndices
        ) {
          assignmentStore.invalidateIndices();
        }
      }
      // Resolve event and resource when joining project
      joinProject() {
        superProto.joinProject.call(this);
        this.setChanged("event", this.get("event"));
        this.setChanged("resource", this.get("resource"));
      }
      // Resolved resource & event as part of commit
      // Normally done earlier in setChanged, but stores might not have been available yet at that point
      calculateInvalidated() {
        var _a4, _b;
        let { event = this.event, resource = this.resource } = this.$changed;
        if (event !== null && !isInstanceOf(event, CoreEventMixin)) {
          const resolved =
            (_a4 = this.eventStore) == null ? void 0 : _a4.getById(event);
          if (resolved) this.setChanged("event", resolved, false);
        }
        if (resource !== null && !isInstanceOf(resource, CoreResourceMixin)) {
          const resolved =
            (_b = this.resourceStore) == null ? void 0 : _b.getById(resource);
          if (resolved) this.setChanged("resource", resolved, false);
        }
      }
      // resourceId and eventId required to be available for new datasets
      finalizeInvalidated(silent) {
        const changed = this.$changed;
        if ("resource" in changed) {
          changed.resourceId = asId(changed.resource);
        }
        if ("event" in changed) {
          changed.eventId = asId(changed.event);
        }
        superProto.finalizeInvalidated.call(this, silent);
      }
      //region Event
      set event(event) {
        this.setChanged("event", event);
        this.setChanged("eventId", asId(event));
      }
      get event() {
        const event = this.get("event");
        return (event == null ? void 0 : event.id) != null ? event : null;
      }
      //endregion
      //region Resource
      set resource(resource) {
        this.setChanged("resource", resource);
        this.setChanged("resourceId", asId(resource));
      }
      get resource() {
        const resource = this.get("resource");
        return (resource == null ? void 0 : resource.id) != null
          ? resource
          : null;
      }
    }
    return CoreAssignmentMixin2;
  },
) {};

// ../Scheduler/lib/Scheduler/model/AssignmentModel.js
var EngineMixin5 = CoreAssignmentMixin;
var AssignmentModel = class extends AssignmentModelMixin_default(
  PartOfProject_default(EngineMixin5.derive(Model)),
) {
  // NOTE: Leave field defs at top to be picked up by jsdoc
  /**
   * Id for event to assign. Can be used as an alternative to `eventId`, but please note that after
   * load it will be populated with the actual event and not its id. This field is not persistable.
   * @field {Scheduler.model.EventModel} event
   * @accepts {String|Number|Scheduler.model.EventModel}
   * @typings {String||Number||Scheduler.model.EventModel||Scheduler.model.TimeSpan}
   * @category Common
   */
  /**
   * Id for resource to assign to. Can be used as an alternative to `resourceId`, but please note that after
   * load it will be populated with the actual resource and not its id. This field is not persistable.
   * @field {Scheduler.model.ResourceModel} resource
   * @accepts {String|Number|Scheduler.model.ResourceModel}
   * @category Common
   */
  static get $name() {
    return "AssignmentModel";
  }
};
AssignmentModel.exposeProperties();
AssignmentModel._$name = "AssignmentModel";

// ../Scheduler/lib/Scheduler/data/mixin/AssignmentStoreMixin.js
var AssignmentStoreMixin_default = (Target) =>
  class AssignmentStoreMixin extends Target {
    static get $name() {
      return "AssignmentStoreMixin";
    }
    /**
     * Add assignments to the store.
     *
     * NOTE: References (event, resource) on the assignments are determined async by a calculation engine. Thus they
     * cannot be directly accessed after using this function.
     *
     * For example:
     *
     * ```javascript
     * const [assignment] = assignmentStore.add({ eventId, resourceId });
     * // assignment.event is not yet available
     * ```
     *
     * To guarantee references are set up, wait for calculations for finish:
     *
     * ```javascript
     * const [assignment] = assignmentStore.add({ eventId, resourceId });
     * await assignmentStore.project.commitAsync();
     * // assignment.event is available (assuming EventStore is loaded and so on)
     * ```
     *
     * Alternatively use `addAsync()` instead:
     *
     * ```javascript
     * const [assignment] = await assignmentStore.addAsync({ eventId, resourceId });
     * // assignment.event is available (assuming EventStore is loaded and so on)
     * ```
     *
     * @param {Scheduler.model.AssignmentModel|Scheduler.model.AssignmentModel[]|AssignmentModelConfig|AssignmentModelConfig[]} records
     * Array of records/data or a single record/data to add to store
     * @param {Boolean} [silent] Specify `true` to suppress events
     * @returns {Scheduler.model.AssignmentModel[]} Added records
     * @function add
     * @category CRUD
     */
    /**
     * Add assignments to the store and triggers calculations directly after. Await this function to have up to date
     * references on the added assignments.
     *
     * ```javascript
     * const [assignment] = await assignmentStore.addAsync({ eventId, resourceId });
     * // assignment.event is available (assuming EventStore is loaded and so on)
     * ```
     *
     * @param {Scheduler.model.AssignmentModel|Scheduler.model.AssignmentModel[]|AssignmentModelConfig|AssignmentModelConfig[]} records
     * Array of records/data or a single record/data to add to store
     * @param {Boolean} [silent] Specify `true` to suppress events
     * @returns {Scheduler.model.AssignmentModel[]} Added records
     * @function addAsync
     * @category CRUD
     * @async
     */
    /**
     * Applies a new dataset to the AssignmentStore. Use it to plug externally fetched data into the store.
     *
     * NOTE: References (assignments, resources) on the assignments are determined async by a calculation engine. Thus
     * they cannot be directly accessed after assigning the new dataset.
     *
     * For example:
     *
     * ```javascript
     * assignmentStore.data = [{ eventId, resourceId }];
     * // assignmentStore.first.event is not yet available
     * ```
     *
     * To guarantee references are available, wait for calculations for finish:
     *
     * ```javascript
     * assignmentStore.data = [{ eventId, resourceId  }];
     * await assignmentStore.project.commitAsync();
     * // assignmentStore.first.event is available
     * ```
     *
     * Alternatively use `loadDataAsync()` instead:
     *
     * ```javascript
     * await assignmentStore.loadDataAsync([{ eventId, resourceId }]);
     * // assignmentStore.first.event is available
     * ```
     *
     * @member {AssignmentModelConfig[]} data
     * @category Records
     */
    /**
     * Applies a new dataset to the AssignmentStore and triggers calculations directly after. Use it to plug externally
     * fetched data into the store.
     *
     * ```javascript
     * await assignmentStore.loadDataAsync([{ eventId, resourceId }]);
     * // assignmentStore.first.event is available
     * ```
     *
     * @param {AssignmentModelConfig[]} data Array of AssignmentModel data objects
     * @function loadDataAsync
     * @category CRUD
     * @async
     */
    static get defaultConfig() {
      return {
        /**
         * CrudManager must load stores in the correct order. Lowest first.
         * @private
         */
        loadPriority: 300,
        /**
         * CrudManager must sync stores in the correct order. Lowest first.
         * @private
         */
        syncPriority: 300,
        storeId: "assignments",
      };
    }
    add(newAssignments, ...args) {
      var _a4;
      newAssignments = ArrayHelper.asArray(newAssignments);
      for (let i = 0; i < newAssignments.length; i++) {
        let assignment = newAssignments[i];
        if (!(assignment instanceof Model)) {
          newAssignments[i] = assignment = this.createRecord(assignment);
        }
        if (
          !this.isSyncingDataOnLoad &&
          this.storage.findIndex(
            "eventResourceKey",
            assignment.eventResourceKey,
            true,
          ) !== -1
        ) {
          throw new Error(
            `Duplicate assignment Event: ${assignment.eventId} to resource: ${assignment.resourceId}`,
          );
        }
        if ((_a4 = assignment.event) == null ? void 0 : _a4.isCreating) {
          assignment.isCreating = true;
        }
      }
      return super.add(newAssignments, ...args);
    }
    includesAssignment(eventId, resourceId) {
      return (
        this.storage.findIndex(
          "eventResourceKey",
          `${eventId}-${resourceId}`,
          true,
        ) !== -1
      );
    }
    setStoreData(data) {
      if (this.usesSingleAssignment) {
        throw new Error(
          "Data loading into AssignmentStore (multi-assignment mode) cannot be combined EventStore data containing resourceId (single-assignment mode)",
        );
      }
      super.setStoreData(data);
    }
    //region Init & destroy
    // This index fixes poor performance when you add large number of events to an event store with large number of
    // events - if cache is missing existing records are iterated n² times.
    // https://github.com/bryntum/support/issues/3154#issuecomment-881336588
    set storage(storage) {
      super.storage = storage;
      this.storage.addIndex({
        property: "eventResourceKey",
        dependentOn: { event: true, resource: true },
        onDuplicate(assignment) {
          console.warn(
            `Duplicate assignment of event ${assignment.eventId} to resource ${assignment.resourceId}`,
          );
        },
      });
    }
    get storage() {
      return this._storage || super.storage;
    }
    //endregion
    //region Stores
    // To not have to do instanceof checks
    get isAssignmentStore() {
      return true;
    }
    //endregion
    //region Recurrence
    /**
     * Returns a "fake" assignment used to identify a certain occurrence of a recurring event.
     * If passed the original event, it returns `originalAssignment`.
     * @param {Scheduler.model.AssignmentModel} originalAssignment
     * @param {Scheduler.model.EventModel} occurrence
     * @returns {Object} Temporary assignment
     * @internal
     */
    getOccurrence(originalAssignment, occurrence) {
      if (
        !originalAssignment ||
        !(occurrence == null ? void 0 : occurrence.isOccurrence)
      ) {
        return originalAssignment;
      }
      const me = this;
      return {
        id: `${occurrence.id}:a${originalAssignment.id}`,
        event: occurrence,
        resource: originalAssignment.resource,
        eventId: occurrence.id,
        resourceId: originalAssignment.resource.id,
        isAssignment: true,
        // This field is required to distinguish this fake assignment when event is being removed from UI
        isOccurrenceAssignment: true,
        // Not being an actual record, instanceMeta is stored on the store instead
        instanceMeta(instanceOrId) {
          return me.occurrenceInstanceMeta(this, instanceOrId);
        },
      };
    }
    // Per fake assignment instance meta, stored on store since fakes are always generated on demand
    occurrenceInstanceMeta(occurrenceAssignment, instanceOrId) {
      const me = this,
        instanceId = instanceOrId.id || instanceOrId,
        { id } = occurrenceAssignment;
      let { occurrenceMeta } = me;
      if (!occurrenceMeta) {
        occurrenceMeta = me.occurrenceMeta = {};
      }
      if (!occurrenceMeta[id]) {
        occurrenceMeta[id] = {};
      }
      return (
        occurrenceMeta[id][instanceId] || (occurrenceMeta[id][instanceId] = {})
      );
    }
    //endregion
    //region Mapping
    /**
     * Maps over event assignments.
     *
     * @param {Scheduler.model.EventModel} event
     * @param {Function} [fn]
     * @param {Function} [filterFn]
     * @returns {Scheduler.model.EventModel[]|Array}
     * @category Assignments
     */
    mapAssignmentsForEvent(event, fn2, filterFn) {
      event = this.eventStore.getById(event);
      const fnSet = Boolean(fn2),
        filterFnSet = Boolean(filterFn);
      if (fnSet || filterFnSet) {
        return event.assignments.reduce((result, assignment) => {
          const mapResult = fnSet ? fn2(assignment) : assignment;
          if (!filterFnSet || filterFn(mapResult)) {
            result.push(mapResult);
          }
          return result;
        }, []);
      }
      return event.assignments;
    }
    /**
     * Maps over resource assignments.
     *
     * @param {Scheduler.model.ResourceModel|Number|String} resource
     * @param {Function} [fn]
     * @param {Function} [filterFn]
     * @returns {Scheduler.model.ResourceModel[]|Array}
     * @category Assignments
     */
    mapAssignmentsForResource(resource, fn2, filterFn) {
      resource = this.resourceStore.getById(resource);
      const fnSet = Boolean(fn2),
        filterFnSet = Boolean(filterFn);
      if (fnSet || filterFnSet) {
        return resource.assignments.reduce((result, assignment) => {
          const mapResult = fnSet ? fn2(assignment) : assignment;
          if (!filterFnSet || filterFn(mapResult)) {
            result.push(mapResult);
          }
          return result;
        }, []);
      }
      return resource.assignments;
    }
    /**
     * Returns all assignments for a given event.
     *
     * @param {Scheduler.model.TimeSpan} event
     * @returns {Scheduler.model.AssignmentModel[]}
     * @category Assignments
     */
    getAssignmentsForEvent(event) {
      return event.assignments;
    }
    /**
     * Removes all assignments for given event
     *
     * @param {Scheduler.model.TimeSpan} event
     * @category Assignments
     */
    removeAssignmentsForEvent(event) {
      return this.remove(event.assignments);
    }
    /**
     * Returns all assignments for a given resource.
     *
     * @param {Scheduler.model.ResourceModel} resource
     * @returns {Scheduler.model.AssignmentModel[]}
     * @category Assignments
     */
    getAssignmentsForResource(resource) {
      resource = this.resourceStore.getById(resource);
      return resource.assignments;
    }
    /**
     * Removes all assignments for given resource
     *
     * @param {Scheduler.model.ResourceModel|*} resource
     * @category Assignments
     */
    removeAssignmentsForResource(resource) {
      this.remove(this.getAssignmentsForResource(resource));
    }
    /**
     * Returns all resources assigned to an event.
     *
     * @param {Scheduler.model.EventModel} event
     * @returns {Scheduler.model.ResourceModel[]}
     * @category Assignments
     */
    getResourcesForEvent(event) {
      return event.resources;
    }
    /**
     * Returns all events assigned to a resource
     *
     * @param {Scheduler.model.ResourceModel|String|Number} resource
     * @returns {Scheduler.model.TimeSpan[]}
     * @category Assignments
     */
    getEventsForResource(resource) {
      resource = this.resourceStore.getById(resource);
      return resource == null ? void 0 : resource.events;
    }
    /**
     * Creates and adds assignment record(s) for a given event and resource(s).
     *
     * @param {Scheduler.model.TimeSpan} event
     * @param {Scheduler.model.ResourceModel|Scheduler.model.ResourceModel[]} resources The resource(s) to assign to the event
     * @param {Function} [assignmentSetupFn] A hook function which takes an assignment as its argument and must return an assignment.
     * @param {Boolean} [removeExistingAssignments] `true` to remove assignments for other resources
     * @returns {Scheduler.model.AssignmentModel[]} An array with the created assignment(s)
     * @category Assign
     */
    assignEventToResource(
      event,
      resources,
      assignmentSetupFn = null,
      removeExistingAssignments = false,
    ) {
      var _a4, _b, _c;
      const me = this,
        toRemove = removeExistingAssignments
          ? new Set(event.assignments)
          : null;
      resources = ArrayHelper.asArray(resources).map((r) => {
        var _a5;
        return (_a5 = r.$original) != null ? _a5 : r;
      });
      if ((_a4 = me.eventStore) == null ? void 0 : _a4.usesSingleAssignment) {
        if ((_b = event.assignments) == null ? void 0 : _b.length) {
          if (!me.isEventAssignedToResource(event, resources[0])) {
            event.resource = resources[0];
          }
          return [];
        } else {
          event.resourceId = (_c = resources[0]) == null ? void 0 : _c.id;
        }
      }
      let newAssignments = [];
      me.suspendAutoCommit();
      resources.forEach((resource) => {
        var _a5;
        const existingAssignment = me.getAssignmentForEventAndResource(
          event,
          resource,
        );
        if (!existingAssignment) {
          const assignment = {
            event,
            resource,
          };
          newAssignments.push(
            (_a5 =
              assignmentSetupFn == null
                ? void 0
                : assignmentSetupFn(assignment)) != null
              ? _a5
              : assignment,
          );
        } else if (removeExistingAssignments) {
          toRemove.delete(existingAssignment);
        }
      });
      newAssignments = me.add(newAssignments);
      if (removeExistingAssignments) {
        me.remove(Array.from(toRemove));
      }
      me.resumeAutoCommit();
      return newAssignments;
    }
    /**
     * Removes assignment record for a given event and resource.
     *
     * @param {Scheduler.model.TimeSpan|String|Number} event
     * @param {Scheduler.model.ResourceModel|String|Number} [resources] The resource to unassign the event from. If omitted, all resources of the events will be unassigned
     * @returns {Scheduler.model.AssignmentModel|Scheduler.model.AssignmentModel[]}
     * @category Assign
     */
    unassignEventFromResource(event, resources) {
      const me = this,
        assignmentsToRemove = [];
      if (!resources) {
        return me.removeAssignmentsForEvent(event);
      }
      resources = ArrayHelper.asArray(resources);
      for (let i = 0; i < resources.length; i++) {
        if (me.isEventAssignedToResource(event, resources[i])) {
          assignmentsToRemove.push(
            me.getAssignmentForEventAndResource(event, resources[i]),
          );
        }
      }
      return me.remove(assignmentsToRemove);
    }
    /**
     * Checks whether an event is assigned to a resource.
     *
     * @param {Scheduler.model.EventModel|String|Number} event Event record or id
     * @param {Scheduler.model.ResourceModel|String|Number} resource Resource record or id
     * @returns {Boolean}
     * @category Assignments
     */
    isEventAssignedToResource(event, resource) {
      return Boolean(this.getAssignmentForEventAndResource(event, resource));
    }
    /**
     * Returns an assignment record for a given event and resource
     *
     * @param {Scheduler.model.EventModel|String|Number} event The event or its id
     * @param {Scheduler.model.ResourceModel|String|Number} resource The resource or its id
     * @returns {Scheduler.model.AssignmentModel}
     * @category Assignments
     */
    getAssignmentForEventAndResource(event, resource) {
      let assignments;
      if (
        !(event = this.eventStore.getById(event)) ||
        !(assignments = event.assignments) || // Also note that resources are looked for in the master store if chained, to handle dragging between
        // schedulers using chained versions of the same resource store. Needed since assignmentStore is shared and
        // might point to wrong resourceStore (can only point to one)
        !(resource = this.resourceStore.$master.getById(resource))
      ) {
        return null;
      }
      return this.getOccurrence(
        assignments.find((a) => {
          var _a4;
          return (
            ((_a4 = a.resource) == null ? void 0 : _a4.$original) ===
            resource.$original
          );
        }),
        event,
      );
    }
    //endregion
  };

// ../Engine/lib/Engine/util/Functions.js
var isNotNumber = (value) => Number(value) !== value;
var CIFromSetOrArrayOrValue = (value) => {
  if (value instanceof Set || value instanceof Array) return CI(value);
  return CI([value]);
};
var delay = (value) => new Promise((resolve) => setTimeout(resolve, value));
var format = (format2, ...values) => {
  return format2.replace(/{(\d+)}/g, (match, number) =>
    typeof values[number] !== "undefined" ? values[number] : match,
  );
};

// ../Engine/lib/Engine/quark/store/AbstractAssignmentStoreMixin.js
var AbstractAssignmentStoreMixin = class extends Mixin(
  [AbstractPartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class AbstractAssignmentStoreMixin2 extends base {
      constructor() {
        super(...arguments);
        this.assignmentsForRemoval = /* @__PURE__ */ new Set();
        this.allAssignmentsForRemoval = false;
      }
      remove(records, silent) {
        this.assignmentsForRemoval = CIFromSetOrArrayOrValue(records).toSet();
        const res = superProto.remove.call(this, records, silent);
        this.assignmentsForRemoval.clear();
        return res;
      }
      removeAll(silent) {
        this.allAssignmentsForRemoval = true;
        const res = superProto.removeAll.call(this, silent);
        this.allAssignmentsForRemoval = false;
        return res;
      }
    }
    return AbstractAssignmentStoreMixin2;
  },
) {};

// ../Engine/lib/Engine/quark/store/CoreAssignmentStoreMixin.js
var emptySet = /* @__PURE__ */ new Set();
var CoreAssignmentStoreMixin = class extends Mixin(
  [AbstractAssignmentStoreMixin, CorePartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class CoreAssignmentStoreMixin2 extends base {
      constructor() {
        super(...arguments);
        this.skipInvalidateIndices = false;
      }
      static get defaultConfig() {
        return {
          modelClass: CoreAssignmentMixin,
          storage: {
            extraKeys: [
              { property: "event", unique: false },
              { property: "resource", unique: false },
              { property: "eventId", unique: false },
            ],
          },
        };
      }
      set data(value) {
        this.allAssignmentsForRemoval = true;
        super.data = value;
        this.allAssignmentsForRemoval = false;
      }
      getEventsAssignments(event) {
        return this.storage.findItem("event", event, true) || emptySet;
      }
      getResourcesAssignments(resource) {
        return (
          this.storage.findItem("resource", resource.$original, true) ||
          emptySet
        );
      }
      updateIndices() {
        this.storage.rebuildIndices();
      }
      invalidateIndices() {
        this.storage.invalidateIndices();
      }
      afterLoadData() {
        this.eventStore && this.linkAssignments(this.eventStore, "event");
        this.resourceStore &&
          this.linkAssignments(this.resourceStore, "resource");
      }
      // Link events/resources to assignments, called when those stores are populated or joined to project
      linkAssignments(store, modelName) {
        store = store.masterStore || store;
        const unresolved =
          this.count && this.storage.findItem(modelName, null, true);
        if (unresolved) {
          for (const assignment of unresolved) {
            const record = store.getById(
              assignment.getCurrentOrProposed(modelName),
            );
            if (record) assignment.setChanged(modelName, record);
          }
          this.invalidateIndices();
        }
      }
      // Unlink events/resources from assignments, called when those stores are cleared
      unlinkAssignments(modelName) {
        this.forEach((assignment) => {
          var _a4, _b, _c;
          return assignment.setChanged(
            modelName,
            (_c =
              (_b = (_a4 = assignment[modelName]) == null ? void 0 : _a4.id) !=
              null
                ? _b
                : assignment == null
                  ? void 0
                  : assignment.getData(modelName)) != null
              ? _c
              : assignment[modelName + "Id"],
          );
        });
        this.invalidateIndices();
      }
      onCommitAsync() {
        this.updateIndices();
      }
    }
    return CoreAssignmentStoreMixin2;
  },
) {};

// ../Scheduler/lib/Scheduler/data/AssignmentStore.js
var EngineMixin6 = PartOfProject_default(
  CoreAssignmentStoreMixin.derive(AjaxStore),
);
var AssignmentStore = class extends AssignmentStoreMixin_default(EngineMixin6) {
  static get defaultConfig() {
    return {
      modelClass: AssignmentModel,
    };
  }
};
__publicField(AssignmentStore, "$name", "AssignmentStore");
AssignmentStore._$name = "AssignmentStore";

// ../Scheduler/lib/Scheduler/model/DependencyBaseModel.js
var canonicalDependencyTypes = ["SS", "SF", "FS", "FF"];
var DependencyBaseModel = class _DependencyBaseModel extends Model {
  static get $name() {
    return "DependencyBaseModel";
  }
  /**
   * Set value for the specified field(s), triggering engine calculations immediately. See
   * {@link Core.data.Model#function-set Model#set()} for arguments.
   **
   * ```javascript
   * dependency.set('from', 2);
   * // dependency.fromEvent is not yet up to date
   *
   * await dependency.setAsync('from', 2);
   * // dependency.fromEvent is up to date
   * ```
   *
   * @param {String|Object} field The field to set value for, or an object with multiple values to set in one call
   * @param {*} [value] Value to set
   * @param {Boolean} [silent=false] Set to true to not trigger events
   * automatically.
   * @function setAsync
   * @category Editing
   * @async
   */
  //region Fields
  /**
   * An enumerable object, containing names for the dependency types integer constants.
   * - 0 StartToStart
   * - 1 StartToEnd
   * - 2 EndToStart
   * - 3 EndToEnd
   * @property {Object}
   * @readonly
   * @category Dependency
   */
  static get Type() {
    return {
      StartToStart: 0,
      StartToEnd: 1,
      EndToStart: 2,
      EndToEnd: 3,
    };
  }
  static get fields() {
    return [
      // 3 mandatory fields
      /**
       * From event, id of source event
       * @field {String|Number} from
       * @category Dependency
       */
      { name: "from" },
      /**
       * To event, id of target event
       * @field {String|Number} to
       * @category Dependency
       */
      { name: "to" },
      /**
       * Dependency type, see static property {@link #property-Type-static}
       * @field {Number} type=2
       * @category Dependency
       */
      { name: "type", type: "int", defaultValue: 2 },
      /**
       * CSS class to apply to lines drawn for the dependency
       * @field {String} cls
       * @category Styling
       */
      { name: "cls", defaultValue: "" },
      /**
       * Bidirectional, drawn with arrows in both directions
       * @field {Boolean} bidirectional
       * @category Dependency
       */
      { name: "bidirectional", type: "boolean" },
      /**
       * Start side on source (top, left, bottom, right)
       * @field {'top'|'left'|'bottom'|'right'} fromSide
       * @category Dependency
       */
      { name: "fromSide", type: "string" },
      /**
       * End side on target (top, left, bottom, right)
       * @field {'top'|'left'|'bottom'|'right'} toSide
       * @category Dependency
       */
      { name: "toSide", type: "string" },
      /**
       * The magnitude of this dependency's lag (the number of units).
       * @field {Number} lag
       * @category Dependency
       */
      { name: "lag", type: "number", allowNull: true, defaultValue: 0 },
      /**
       * The units of this dependency's lag, defaults to "d" (days). Valid values are:
       *
       * - "ms" (milliseconds)
       * - "s" (seconds)
       * - "m" (minutes)
       * - "h" (hours)
       * - "d" (days)
       * - "w" (weeks)
       * - "M" (months)
       * - "y" (years)
       *
       * This field is readonly after creation, to change `lagUnit` use {@link #function-setLag setLag()}.
       * @field {DurationUnitShort} lagUnit
       * @category Dependency
       * @readonly
       */
      {
        name: "lagUnit",
        type: "string",
        defaultValue: "d",
      },
      { name: "highlighted", persist: false, internal: true },
    ];
  }
  // fromEvent/toEvent defined in CoreDependencyMixin in engine
  /**
   * Gets/sets the source event of the dependency.
   *
   * Accepts multiple formats but always returns an {@link Scheduler.model.EventModel}.
   *
   * **NOTE:** This is not a proper field but rather an alias, it will be serialized but cannot be remapped. If you
   * need to remap, consider using {@link #field-from} instead.
   *
   * @field {Scheduler.model.EventModel} fromEvent
   * @accepts {String|Number|Scheduler.model.EventModel}
   * @category Dependency
   */
  /**
   * Gets/sets the target event of the dependency.
   *
   * Accepts multiple formats but always returns an {@link Scheduler.model.EventModel}.
   *
   * **NOTE:** This is not a proper field but rather an alias, it will be serialized but cannot be remapped. If you
   * need to remap, consider using {@link #field-to} instead.
   *
   * @field {Scheduler.model.EventModel} toEvent
   * @accepts {String|Number|Scheduler.model.EventModel}
   * @category Dependency
   */
  //endregion
  //region Init
  construct(data) {
    const from = data[this.fieldMap.from.dataSource],
      to = data[this.fieldMap.to.dataSource];
    if (from != null) {
      data.fromEvent = from;
    }
    if (to != null) {
      data.toEvent = to;
    }
    super.construct(...arguments);
  }
  //endregion
  get eventStore() {
    var _a4;
    return (
      this.eventStore ||
      ((_a4 = this.unjoinedStores[0]) == null ? void 0 : _a4.eventStore)
    );
  }
  set from(value) {
    const { fromEvent } = this;
    if (
      (fromEvent == null ? void 0 : fromEvent.isModel) &&
      fromEvent.id === value
    ) {
      this.set("from", value);
    } else {
      this.fromEvent = value;
    }
  }
  get from() {
    return this.get("from");
  }
  set to(value) {
    const { toEvent } = this;
    if ((toEvent == null ? void 0 : toEvent.isModel) && toEvent.id === value) {
      this.set("to", value);
    } else {
      this.toEvent = value;
    }
  }
  get to() {
    return this.get("to");
  }
  /**
   * Alias to dependency type, but when set resets {@link #field-fromSide} & {@link #field-toSide} to null as well.
   *
   * @property {Number}
   * @category Dependency
   */
  get hardType() {
    return this.getHardType();
  }
  set hardType(type) {
    this.setHardType(type);
  }
  /**
   * Returns dependency hard type, see {@link #property-hardType}.
   *
   * @returns {Number}
   * @category Dependency
   */
  getHardType() {
    return this.get("type");
  }
  /**
   * Sets dependency {@link #field-type} and resets {@link #field-fromSide} and {@link #field-toSide} to null.
   *
   * @param {Number} type
   * @category Dependency
   */
  setHardType(type) {
    let result;
    if (type !== this.hardType) {
      result = this.set({
        type,
        fromSide: null,
        toSide: null,
      });
    }
    return result;
  }
  get lag() {
    return this.get("lag");
  }
  set lag(lag) {
    this.setLag(lag);
  }
  /**
   * Sets lag and lagUnit in one go. Only allowed way to change lagUnit, the lagUnit field is readonly after creation
   * @param {Number|String|Object} lag The lag value. May be just a numeric magnitude, or a full string descriptor eg '1d'
   * @param {DurationUnitShort} [lagUnit] Unit for numeric lag value, see
   * {@link #field-lagUnit} for valid values
   * @category Dependency
   */
  setLag(lag, lagUnit = this.lagUnit) {
    if (arguments.length === 1) {
      if (typeof lag === "number") {
        this.lag = lag;
      } else {
        lag = DateHelper.parseDuration(lag);
        this.set({
          lag: lag.magnitude,
          lagUnit: lag.unit,
        });
      }
      return;
    }
    lag = parseFloat(lag);
    this.set({
      lag,
      lagUnit,
    });
  }
  getLag() {
    if (this.lag) {
      return `${this.lag < 0 ? "-" : "+"}${Math.abs(this.lag)}${DateHelper.getShortNameOfUnit(this.lagUnit)}`;
    }
    return "";
  }
  /**
   * Property which encapsulates the lag's magnitude and units. An object which contains two properties:
   * @property {Core.data.Duration}
   * @property {Number} fullLag.magnitude The magnitude of the duration
   * @property {DurationUnitShort} fullLag.unit The unit in which the duration is measured, eg
   * `'d'` for days
   * @category Dependency
   */
  get fullLag() {
    return new Duration({
      unit: this.lagUnit,
      magnitude: this.lag,
    });
  }
  set fullLag(lag) {
    if (typeof lag === "string") {
      this.setLag(lag);
    } else {
      this.setLag(lag.magnitude, lag.unit);
    }
  }
  /**
   * Returns true if the linked events have been persisted (e.g. neither of them are 'phantoms')
   *
   * @property {Boolean}
   * @readonly
   * @category Editing
   */
  get isPersistable() {
    const me = this,
      { stores: stores2, unjoinedStores } = me,
      store = stores2[0];
    let result;
    if (store) {
      const { fromEvent, toEvent } = me,
        crudManager = store.crudManager;
      result =
        fromEvent &&
        (crudManager || !fromEvent.hasGeneratedId) &&
        toEvent &&
        (crudManager || !toEvent.hasGeneratedId);
    } else {
      result = Boolean(unjoinedStores[0]);
    }
    return result && super.isPersistable;
  }
  getDateRange() {
    const { fromEvent, toEvent } = this;
    if (
      (fromEvent == null ? void 0 : fromEvent.isScheduled) &&
      (toEvent == null ? void 0 : toEvent.isScheduled)
    ) {
      const Type = _DependencyBaseModel.Type;
      let sourceDate, targetDate;
      switch (this.type) {
        case Type.StartToStart:
          sourceDate = fromEvent.startDateMS;
          targetDate = toEvent.startDateMS;
          break;
        case Type.StartToEnd:
          sourceDate = fromEvent.startDateMS;
          targetDate = toEvent.endDateMS;
          break;
        case Type.EndToEnd:
          sourceDate = fromEvent.endDateMS;
          targetDate = toEvent.endDateMS;
          break;
        case Type.EndToStart:
          sourceDate = fromEvent.endDateMS;
          targetDate = toEvent.startDateMS;
          break;
        default:
          throw new Error("Invalid dependency type: " + this.type);
      }
      return {
        start: Math.min(sourceDate, targetDate),
        end: Math.max(sourceDate, targetDate),
      };
    }
    return null;
  }
  /**
   * Applies given CSS class to dependency, the value doesn't persist
   *
   * @param {String} cls
   * @category Dependency
   */
  highlight(cls2) {
    var _a4, _b;
    const classes =
      (_b = (_a4 = this.highlighted) == null ? void 0 : _a4.split(" ")) != null
        ? _b
        : [];
    if (!classes.includes(cls2)) {
      this.highlighted = classes.concat(cls2).join(" ");
    }
  }
  /**
   * Removes given CSS class from dependency if applied, the value doesn't persist
   *
   * @param {String} cls
   * @category Dependency
   */
  unhighlight(cls2) {
    const { highlighted } = this;
    if (highlighted) {
      const classes = highlighted.split(" "),
        index = classes.indexOf(cls2);
      if (index >= 0) {
        classes.splice(index, 1);
        this.highlighted = classes.join(" ");
      }
    }
  }
  /**
   * Checks if the given CSS class is applied to dependency.
   *
   * @param {String} cls
   * @returns {Boolean}
   * @category Dependency
   */
  isHighlightedWith(cls2) {
    return this.highlighted && this.highlighted.split(" ").includes(cls2);
  }
  getConnectorString(raw) {
    const rawValue = canonicalDependencyTypes[this.type];
    if (raw) {
      return rawValue;
    }
    if (this.type === _DependencyBaseModel.Type.EndToStart) {
      return "";
    }
    return rawValue;
  }
  // getConnectorStringFromType(type, raw) {
  //     const rawValue = canonicalDependencyTypes[type];
  //
  //     if (raw) {
  //         return rawValue;
  //     }
  //
  //     // FS => empty string; it's the default
  //     if (type === DependencyBaseModel.Type.EndToStart) {
  //         return '';
  //     }
  //
  //     const locale = LocaleManager.locale;
  //
  //     // See if there is a local version of SS, SF or FF
  //     if (locale) {
  //         const localized = locale.Scheduler && locale.Scheduler[rawValue];
  //         if (localized) {
  //             return localized;
  //         }
  //     }
  //
  //     return rawValue;
  // }
  // getConnectorString(raw) {
  //     return this.getConnectorStringFromType(this.type);
  // }
  // * getConnectorStringGenerator(raw) {
  //     return this.getConnectorStringFromType(yield this.$.type);
  // }
  toString() {
    return `${this.from}${this.getConnectorString()}${this.getLag()}`;
  }
  /**
   * Returns `true` if the dependency is valid. It is considered valid if it has a valid type and both from and to
   * events are set and pointing to different events.
   *
   * @property {Boolean}
   * @typings ignore
   * @category Editing
   */
  get isValid() {
    const { fromEvent, toEvent, type } = this;
    return (
      typeof type === "number" && fromEvent && toEvent && fromEvent !== toEvent
    );
  }
  get fromEventName() {
    var _a4;
    return ((_a4 = this.fromEvent) == null ? void 0 : _a4.name) || "";
  }
  get toEventName() {
    var _a4;
    return ((_a4 = this.toEvent) == null ? void 0 : _a4.name) || "";
  }
  //region STM hooks
  shouldRecordFieldChange(fieldName, oldValue, newValue) {
    var _a4;
    if (!super.shouldRecordFieldChange(fieldName, oldValue, newValue)) {
      return false;
    }
    if (
      fieldName === "from" ||
      fieldName === "to" ||
      fieldName === "fromEvent" ||
      fieldName === "toEvent"
    ) {
      const eventStore = (_a4 = this.project) == null ? void 0 : _a4.eventStore;
      if (
        eventStore &&
        eventStore.oldIdMap[oldValue] === eventStore.getById(newValue)
      ) {
        return false;
      }
    }
    return true;
  }
  //endregion
};
DependencyBaseModel.exposeProperties();
DependencyBaseModel._$name = "DependencyBaseModel";

// ../Engine/lib/Engine/quark/model/scheduler_core/CoreDependencyMixin.js
var CoreDependencyMixin = class extends Mixin(
  [CorePartOfProjectModelMixin],
  (base) => {
    const superProto = base.prototype;
    class CoreDependencyMixin2 extends base {
      static get fields() {
        return [
          { name: "fromEvent", isEqual: (a, b) => a === b, persist: false },
          { name: "toEvent", isEqual: (a, b) => a === b, persist: false },
        ];
      }
      // Resolve early + update indices to have buckets ready before commit
      setChanged(field2, value, invalidate) {
        var _a4, _b, _c;
        let update = false;
        if (field2 === "fromEvent" || field2 === "toEvent") {
          const event = isInstanceOf(value, CoreEventMixin)
            ? value
            : (_a4 = this.eventStore) == null
              ? void 0
              : _a4.getById(value);
          if (event) update = true;
          value = event || value;
        }
        superProto.setChanged.call(this, field2, value, invalidate, true);
        if (
          update &&
          !this.project.isPerformingCommit &&
          !((_b = this.dependencyStore) == null ? void 0 : _b.isLoadingData)
        ) {
          (_c = this.dependencyStore) == null ? void 0 : _c.invalidateIndices();
        }
      }
      // Resolve events when joining project
      joinProject() {
        superProto.joinProject.call(this);
        this.setChanged("fromEvent", this.get("fromEvent"));
        this.setChanged("toEvent", this.get("toEvent"));
      }
      // Resolved events as part of commit
      // Normally done earlier in setChanged, but stores might not have been available yet at that point
      calculateInvalidated() {
        var _a4, _b;
        let { fromEvent, toEvent } = this.$changed;
        if (fromEvent !== null && !isInstanceOf(fromEvent, CoreEventMixin)) {
          const resolved =
            (_a4 = this.eventStore) == null ? void 0 : _a4.getById(fromEvent);
          if (resolved) this.$changed.fromEvent = resolved;
        }
        if (toEvent !== null && !isInstanceOf(toEvent, CoreEventMixin)) {
          const resolved =
            (_b = this.eventStore) == null ? void 0 : _b.getById(toEvent);
          if (resolved) this.$changed.toEvent = resolved;
        }
      }
      //region Events
      // Not using "propose" mechanism from CoreEventMixin, because buckets are expected to be up to date right away
      set fromEvent(fromEvent) {
        this.setChanged("fromEvent", fromEvent);
      }
      get fromEvent() {
        const fromEvent = this.get("fromEvent");
        return (fromEvent == null ? void 0 : fromEvent.id) != null
          ? fromEvent
          : null;
      }
      set toEvent(toEvent) {
        this.setChanged("toEvent", toEvent);
      }
      get toEvent() {
        const toEvent = this.get("toEvent");
        return (toEvent == null ? void 0 : toEvent.id) != null ? toEvent : null;
      }
    }
    return CoreDependencyMixin2;
  },
) {};

// ../Scheduler/lib/Scheduler/model/DependencyModel.js
var EngineMixin7 = CoreDependencyMixin;
var DependencyModel = class extends PartOfProject_default(
  EngineMixin7.derive(DependencyBaseModel),
) {
  static get $name() {
    return "DependencyModel";
  }
  // Determines the type of dependency based on fromSide and toSide
  getTypeFromSides(fromSide, toSide, rtl) {
    const types = DependencyBaseModel.Type,
      startSide = rtl ? "right" : "left",
      endSide = rtl ? "left" : "right";
    if (fromSide === startSide) {
      return toSide === startSide ? types.StartToStart : types.StartToEnd;
    }
    return toSide === endSide ? types.EndToEnd : types.EndToStart;
  }
};
DependencyModel.exposeProperties();
DependencyModel._$name = "DependencyModel";

// ../Scheduler/lib/Scheduler/data/mixin/DependencyStoreMixin.js
var DependencyStoreMixin_default = (Target) =>
  class DependencyStoreMixin extends Target {
    static get $name() {
      return "DependencyStoreMixin";
    }
    /**
     * Add dependencies to the store.
     *
     * NOTE: References (fromEvent, toEvent) on the dependencies are determined async by a calculation engine. Thus they
     * cannot be directly accessed after using this function.
     *
     * For example:
     *
     * ```javascript
     * const [dependency] = dependencyStore.add({ from, to });
     * // dependency.fromEvent is not yet available
     * ```
     *
     * To guarantee references are set up, wait for calculations for finish:
     *
     * ```javascript
     * const [dependency] = dependencyStore.add({ from, to });
     * await dependencyStore.project.commitAsync();
     * // dependency.fromEvent is available (assuming EventStore is loaded and so on)
     * ```
     *
     * Alternatively use `addAsync()` instead:
     *
     * ```javascript
     * const [dependency] = await dependencyStore.addAsync({ from, to });
     * // dependency.fromEvent is available (assuming EventStore is loaded and so on)
     * ```
     *
     * @param {Scheduler.model.DependencyModel|Scheduler.model.DependencyModel[]|DependencyModelConfig|DependencyModelConfig[]} records
     * Array of records/data or a single record/data to add to store
     * @param {Boolean} [silent] Specify `true` to suppress events
     * @returns {Scheduler.model.DependencyModel[]} Added records
     * @function add
     * @category CRUD
     */
    /**
     * Add dependencies to the store and triggers calculations directly after. Await this function to have up to date
     * references on the added dependencies.
     *
     * ```javascript
     * const [dependency] = await dependencyStore.addAsync({ from, to });
     * // dependency.fromEvent is available (assuming EventStore is loaded and so on)
     * ```
     *
     * @param {Scheduler.model.DependencyModel|Scheduler.model.DependencyModel[]|DependencyModelConfig|DependencyModelConfig[]} records
     * Array of records/data or a single record/data to add to store
     * @param {Boolean} [silent] Specify `true` to suppress events
     * @returns {Scheduler.model.DependencyModel[]} Added records
     * @function addAsync
     * @category CRUD
     * @async
     */
    /**
     * Applies a new dataset to the DependencyStore. Use it to plug externally fetched data into the store.
     *
     * NOTE: References (fromEvent, toEvent) on the dependencies are determined async by a calculation engine. Thus
     * they cannot be directly accessed after assigning the new dataset.
     *
     * For example:
     *
     * ```javascript
     * dependencyStore.data = [{ from, to }];
     * // dependencyStore.first.fromEvent is not yet available
     * ```
     *
     * To guarantee references are available, wait for calculations for finish:
     *
     * ```javascript
     * dependencyStore.data = [{ from, to }];
     * await dependencyStore.project.commitAsync();
     * // dependencyStore.first.fromEvent is available
     * ```
     *
     * Alternatively use `loadDataAsync()` instead:
     *
     * ```javascript
     * await dependencyStore.loadDataAsync([{ from, to }]);
     * // dependencyStore.first.fromEvent is available
     * ```
     *
     * @member {DependencyModelConfig[]} data
     * @category Records
     */
    /**
     * Applies a new dataset to the DependencyStore and triggers calculations directly after. Use it to plug externally
     * fetched data into the store.
     *
     * ```javascript
     * await dependencyStore.loadDataAsync([{ from, to }]);
     * // dependencyStore.first.fromEvent is available
     * ```
     *
     * @param {DependencyModelConfig[]} data Array of DependencyModel data objects
     * @function loadDataAsync
     * @category CRUD
     * @async
     */
    static get defaultConfig() {
      return {
        /**
         * CrudManager must load stores in the correct order. Lowest first.
         * @private
         */
        loadPriority: 400,
        /**
         * CrudManager must sync stores in the correct order. Lowest first.
         * @private
         */
        syncPriority: 400,
        storeId: "dependencies",
      };
    }
    reduceEventDependencies(
      event,
      reduceFn,
      result,
      flat = true,
      depsGetterFn,
    ) {
      depsGetterFn =
        depsGetterFn || ((event2) => this.getEventDependencies(event2));
      event = ArrayHelper.asArray(event);
      event.reduce((result2, event2) => {
        if (event2.children && !flat) {
          event2.traverse((evt) => {
            result2 = depsGetterFn(evt).reduce(reduceFn, result2);
          });
        } else {
          result2 = depsGetterFn(event2).reduce(reduceFn, result2);
        }
      }, result);
      return result;
    }
    mapEventDependencies(event, fn2, filterFn, flat, depsGetterFn) {
      return this.reduceEventDependencies(
        event,
        (result, dependency) => {
          filterFn(dependency) && result.push(dependency);
          return result;
        },
        [],
        flat,
        depsGetterFn,
      );
    }
    mapEventPredecessors(event, fn2, filterFn, flat) {
      return this.reduceEventPredecessors(
        event,
        (result, dependency) => {
          filterFn(dependency) && result.push(dependency);
          return result;
        },
        [],
        flat,
      );
    }
    mapEventSuccessors(event, fn2, filterFn, flat) {
      return this.reduceEventSuccessors(
        event,
        (result, dependency) => {
          filterFn(dependency) && result.push(dependency);
          return result;
        },
        [],
        flat,
      );
    }
    /**
     * Returns all dependencies for a certain event (both incoming and outgoing)
     *
     * @param {Scheduler.model.EventModel} event
     * @returns {Scheduler.model.DependencyModel[]}
     */
    getEventDependencies(event) {
      return [].concat(event.predecessors || [], event.successors || []);
    }
    removeEventDependencies(event) {
      this.remove(this.getEventDependencies(event));
    }
    removeEventPredecessors(event) {
      this.remove(event.predecessors);
    }
    removeEventSuccessors(event, flat) {
      this.remove(event.successors);
    }
    getBySourceTargetId(key) {
      return this.records.find(
        (r) =>
          key ==
          this.constructor.makeDependencySourceTargetCompositeKey(r.from, r.to),
      );
    }
    /**
     * Returns dependency model instance linking tasks with given ids. The dependency can be forward (from 1st
     * task to 2nd) or backward (from 2nd to 1st).
     *
     * @param {Scheduler.model.EventModel|String} sourceEvent 1st event
     * @param {Scheduler.model.EventModel|String} targetEvent 2nd event
     * @returns {Scheduler.model.DependencyModel}
     */
    getDependencyForSourceAndTargetEvents(sourceEvent, targetEvent) {
      sourceEvent = Model.asId(sourceEvent);
      targetEvent = Model.asId(targetEvent);
      return this.getBySourceTargetId(
        this.constructor.makeDependencySourceTargetCompositeKey(
          sourceEvent,
          targetEvent,
        ),
      );
    }
    /**
     * Returns a dependency model instance linking given events if such dependency exists in the store.
     * The dependency can be forward (from 1st event to 2nd) or backward (from 2nd to 1st).
     *
     * @param {Scheduler.model.EventModel|String} sourceEvent
     * @param {Scheduler.model.EventModel|String} targetEvent
     * @returns {Scheduler.model.DependencyModel}
     */
    getEventsLinkingDependency(sourceEvent, targetEvent) {
      return (
        this.getDependencyForSourceAndTargetEvents(sourceEvent, targetEvent) ||
        this.getDependencyForSourceAndTargetEvents(targetEvent, sourceEvent)
      );
    }
    /**
     * Validation method used to validate a dependency. Override and return `true` to indicate that an
     * existing dependency between two tasks is valid. For a new dependency being created please see
     * {@link #function-isValidDependencyToCreate}.
     *
     * @param {Scheduler.model.DependencyModel|Scheduler.model.TimeSpan|Number|String} dependencyOrFromId The dependency
     * model, the from task/event or the id of the from task/event
     * @param {Scheduler.model.TimeSpan|Number|String} [toId] To task/event or id thereof if the first parameter is not
     * a dependency record
     * @param {Number} [type] Dependency {@link Scheduler.model.DependencyBaseModel#property-Type-static} if the first
     * parameter is not a dependency model instance.
     * @returns {Boolean}
     */
    async isValidDependency(dependencyOrFromId, toId, type) {
      let fromEvent = dependencyOrFromId,
        toEvent = toId;
      if (dependencyOrFromId == null) {
        return false;
      }
      if (dependencyOrFromId.isDependencyModel) {
        ({ fromEvent, toEvent } = dependencyOrFromId);
      }
      fromEvent = this.eventStore.getById(fromEvent);
      toEvent = this.eventStore.getById(toEvent);
      if (fromEvent && toEvent) {
        if (!fromEvent.project || !toEvent.project) {
          return false;
        }
        return this.project.isValidDependency(fromEvent, toEvent, type);
      }
      return dependencyOrFromId !== toId;
    }
    /**
     * Validation method used to validate a dependency while creating. Override and return `true` to indicate that
     * a new dependency is valid to be created.
     *
     * @param {Scheduler.model.TimeSpan|Number|String} fromId From event/task or id
     * @param {Scheduler.model.TimeSpan|Number|String} toId To event/task or id
     * @param {Number} type Dependency {@link Scheduler.model.DependencyBaseModel#property-Type-static}
     * @returns {Boolean}
     */
    isValidDependencyToCreate(fromId, toId, type) {
      return this.isValidDependency(fromId, toId, type);
    }
    /**
     * Returns all dependencies highlighted with the given CSS class
     *
     * @param {String} cls
     * @returns {Scheduler.model.DependencyBaseModel[]}
     */
    getHighlightedDependencies(cls2) {
      return this.records.reduce((result, dep) => {
        if (dep.isHighlightedWith(cls2)) result.push(dep);
        return result;
      }, []);
    }
    static makeDependencySourceTargetCompositeKey(from, to) {
      return `source(${from})-target(${to})`;
    }
    //region Product neutral
    getTimeSpanDependencies(record) {
      return this.getEventDependencies(record);
    }
    //endregion
  };

// ../Engine/lib/Engine/quark/store/AbstractDependencyStoreMixin.js
var AbstractDependencyStoreMixin = class extends Mixin(
  [AbstractPartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class AbstractDependencyStoreMixin2 extends base {
      constructor() {
        super(...arguments);
        this.dependenciesForRemoval = /* @__PURE__ */ new Set();
        this.allDependenciesForRemoval = false;
      }
      remove(records, silent) {
        this.dependenciesForRemoval = CIFromSetOrArrayOrValue(records).toSet();
        const res = superProto.remove.call(this, records, silent);
        this.dependenciesForRemoval.clear();
        return res;
      }
      removeAll(silent) {
        this.allDependenciesForRemoval = true;
        const res = superProto.removeAll.call(this, silent);
        this.allDependenciesForRemoval = false;
        return res;
      }
    }
    return AbstractDependencyStoreMixin2;
  },
) {};

// ../Engine/lib/Engine/quark/store/CoreDependencyStoreMixin.js
var emptySet2 = /* @__PURE__ */ new Set();
var CoreDependencyStoreMixin = class extends Mixin(
  [AbstractDependencyStoreMixin, CorePartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class CoreDependencyStoreMixin2 extends base {
      constructor() {
        super(...arguments);
        this.dependenciesForRemoval = /* @__PURE__ */ new Set();
        this.allDependenciesForRemoval = false;
      }
      static get defaultConfig() {
        return {
          modelClass: CoreDependencyMixin,
          storage: {
            extraKeys: [
              { property: "fromEvent", unique: false },
              { property: "toEvent", unique: false },
            ],
          },
        };
      }
      getIncomingDepsForEvent(event) {
        return this.storage.findItem("toEvent", event) || emptySet2;
      }
      getOutgoingDepsForEvent(event) {
        return this.storage.findItem("fromEvent", event) || emptySet2;
      }
      set data(value) {
        this.allDependenciesForRemoval = true;
        super.data = value;
        this.allDependenciesForRemoval = false;
      }
      updateIndices() {
        this.storage.rebuildIndices();
      }
      invalidateIndices() {
        this.storage.invalidateIndices();
      }
      onCommitAsync() {
        this.updateIndices();
      }
    }
    return CoreDependencyStoreMixin2;
  },
) {};

// ../Scheduler/lib/Scheduler/data/DependencyStore.js
var EngineMixin8 = PartOfProject_default(
  CoreDependencyStoreMixin.derive(AjaxStore),
);
var DependencyStore = class extends DependencyStoreMixin_default(
  EngineMixin8.derive(AjaxStore),
) {
  static get defaultConfig() {
    return {
      modelClass: DependencyModel,
    };
  }
};
DependencyStore._$name = "DependencyStore";

// ../Scheduler/lib/Scheduler/crud/mixin/AbstractCrudManagerValidation.js
var AbstractCrudManagerValidation_default = (Target) =>
  class AbstractCrudManagerValidation extends Target {
    static get $name() {
      return "AbstractCrudManagerValidation";
    }
    static get configurable() {
      return {
        /**
         * This config validates the response structure for requests made by the Crud Manager.
         * When `true`, the Crud Manager checks every parsed response structure for errors
         * and if the response format is invalid, a warning is logged to the browser console.
         *
         * The config is intended to help developers implementing backend integration.
         *
         * @config {Boolean}
         * @default
         * @category CRUD
         */
        validateResponse: true,
        /**
         * When `true` treats parsed responses without `success` property as successful.
         * In this mode a parsed response is treated as invalid if it has explicitly set `success : false`.
         * @config {Boolean}
         * @default
         * @category CRUD
         */
        skipSuccessProperty: true,
        crudLoadValidationWarningPrefix: "CrudManager load response error(s):",
        crudSyncValidationWarningPrefix: "CrudManager sync response error(s):",
        supportShortSyncResponseNote:
          'Note: Please consider enabling "supportShortSyncResponse" option to allow less detailed sync responses (https://bryntum.com/products/scheduler/docs/api/Scheduler/crud/AbstractCrudManagerMixin#config-supportShortSyncResponse)',
        disableValidationNote:
          'Note: To disable this validation please set the "validateResponse" config to false',
      };
    }
    get crudLoadValidationMandatoryStores() {
      return [];
    }
    getStoreLoadResponseWarnings(storeInfo, responded, expectedResponse) {
      const messages = [],
        { storeId } = storeInfo,
        mandatoryStores = this.crudLoadValidationMandatoryStores,
        result = { [storeId]: {} };
      if (responded) {
        if (!responded.rows) {
          messages.push(
            `- "${storeId}" store section should have a "rows" property with an array of the store records.`,
          );
          result[storeId].rows = ["..."];
        }
      } else if (
        mandatoryStores == null ? void 0 : mandatoryStores.includes(storeId)
      ) {
        messages.push(
          `- No "${storeId}" store section found. It should contain the store data.`,
        );
        result[storeId].rows = ["..."];
      }
      if (messages.length) {
        Object.assign(expectedResponse, result);
      }
      return messages;
    }
    getLoadResponseWarnings(response) {
      const messages = [],
        expectedResponse = {};
      if (!this.skipSuccessProperty) {
        expectedResponse.success = true;
      }
      this.forEachCrudStore((store, storeId, storeInfo) => {
        messages.push(
          ...this.getStoreLoadResponseWarnings(
            storeInfo,
            response == null ? void 0 : response[storeId],
            expectedResponse,
          ),
        );
      });
      if (messages.length) {
        messages.push(
          "Please adjust your response to look like this:\n" +
            JSON.stringify(expectedResponse, null, 4).replace(
              /"\.\.\."/g,
              "...",
            ),
        );
        messages.push(this.disableValidationNote);
      }
      return messages;
    }
    validateLoadResponse(response) {
      const messages = this.getLoadResponseWarnings(response);
      if (messages.length) {
        console.warn(
          this.crudLoadValidationWarningPrefix + "\n" + messages.join("\n"),
        );
      }
    }
    getStoreSyncResponseWarnings(
      storeInfo,
      requested,
      responded,
      expectedResponse,
    ) {
      const messages = [],
        missingRows = [],
        missingRemoved = [],
        { storeId } = storeInfo,
        result = { [storeId]: {} },
        phantomIdField = storeInfo.phantomIdField || this.phantomIdField,
        { modelClass } = storeInfo.store,
        { idField } = modelClass,
        respondedRows = (responded == null ? void 0 : responded.rows) || [],
        respondedRemoved =
          (responded == null ? void 0 : responded.removed) || [];
      let showSupportShortSyncResponseNote = false;
      if (requested == null ? void 0 : requested.added) {
        missingRows.push(
          ...requested.added
            .filter((record) => {
              return (
                !respondedRows.find(
                  (row) => row[phantomIdField] == record[phantomIdField],
                ) &&
                !respondedRemoved.find(
                  (row) =>
                    row[phantomIdField] == record[phantomIdField] ||
                    row[idField] == record[phantomIdField],
                )
              );
            })
            .map((record) => ({
              [phantomIdField]: record[phantomIdField],
              [idField]: "...",
            })),
        );
        if (missingRows.length) {
          const missingIds = missingRows
            .map((row) => "#" + row[phantomIdField])
            .join(", ");
          messages.push(
            `- "${storeId}" store "rows" section should mention added record(s) ${missingIds} sent in the request. It should contain the added records identifiers (both phantom and "real" ones assigned by the backend).`,
          );
        }
      }
      if (this.supportShortSyncResponse) {
        if (!missingRows.length && responded) {
          if (typeof responded !== "object" || Array.isArray(responded)) {
            messages.push(`- "${storeId}" store section should be an Object.`);
            result[storeId]["..."] = "...";
          }
          if (responded.rows && !Array.isArray(responded.rows)) {
            messages.push(
              `- "${storeId}" store "rows" section should be an array`,
            );
            missingRows.push("...");
          }
          if (responded.removed && !Array.isArray(responded.removed)) {
            messages.push(
              `- "${storeId}" store "removed" section should be an array:`,
            );
            missingRemoved.push("...");
          }
        }
      } else {
        if (requested == null ? void 0 : requested.updated) {
          const missingUpdatedRows = requested.updated
            .filter(
              (record) =>
                !respondedRows.find((row) => row[idField] == record[idField]),
            )
            .map((record) => ({ [idField]: record[idField] }));
          missingRows.push(...missingUpdatedRows);
          if (missingUpdatedRows.length) {
            const missingIds = missingUpdatedRows
              .map((row) => "#" + row[idField])
              .join(", ");
            messages.push(
              `- "${storeId}" store "rows" section should mention updated record(s) ${missingIds} sent in the request. It should contain the updated record identifiers.`,
            );
            showSupportShortSyncResponseNote = true;
          }
        }
        if (missingRows.length) {
          missingRows.push("...");
        }
        if (requested == null ? void 0 : requested.removed) {
          missingRemoved.push(
            ...requested.removed
              .filter(
                (record) =>
                  !respondedRows.find((row) => row[idField] == record[idField]),
              )
              .map((record) => ({ [idField]: record[idField] })),
          );
          if (missingRemoved.length) {
            const missingIds = missingRemoved
              .map((row) => "#" + row[idField])
              .join(", ");
            messages.push(
              `- "${storeId}" store "removed" section should mention removed record(s) ${missingIds} sent in the request. It should contain the removed record identifiers.`,
            );
            result[storeId].removed = missingRemoved;
            missingRemoved.push("...");
            showSupportShortSyncResponseNote = true;
          }
        }
      }
      if (missingRows.length) {
        result[storeId].rows = missingRows;
      }
      if (!messages.length) {
        delete result[storeId];
      }
      Object.assign(expectedResponse, result);
      return { messages, showSupportShortSyncResponseNote };
    }
    getSyncResponseWarnings(response, requestDesc) {
      const messages = [],
        expectedResponse = {},
        request = requestDesc.pack;
      if (!this.skipSuccessProperty) {
        expectedResponse.success = true;
      }
      let showSupportShortSyncResponseNote = false;
      this.forEachCrudStore((store, storeId, storeInfo) => {
        const warnings = this.getStoreSyncResponseWarnings(
          storeInfo,
          request == null ? void 0 : request[storeId],
          response[storeId],
          expectedResponse,
        );
        showSupportShortSyncResponseNote =
          showSupportShortSyncResponseNote ||
          warnings.showSupportShortSyncResponseNote;
        messages.push(...warnings.messages);
      });
      if (messages.length) {
        messages.push(
          "Please adjust your response to look like this:\n" +
            JSON.stringify(expectedResponse, null, 4)
              .replace(/"\.\.\.":\s*"\.\.\."/g, ",,,")
              .replace(/"\.\.\."/g, "..."),
        );
        if (showSupportShortSyncResponseNote) {
          messages.push(this.supportShortSyncResponseNote);
        }
        messages.push(this.disableValidationNote);
      }
      return messages;
    }
    validateSyncResponse(response, request) {
      const messages = this.getSyncResponseWarnings(response, request);
      if (messages.length) {
        console.warn(
          this.crudSyncValidationWarningPrefix + "\n" + messages.join("\n"),
        );
      }
    }
  };

// ../Scheduler/lib/Scheduler/crud/AbstractCrudManagerMixin.js
var AbstractCrudManagerError = class extends Error {};
var CrudManagerRequestError = class extends AbstractCrudManagerError {
  constructor(cfg = {}) {
    var _a4, _b;
    super(
      cfg.message ||
        (cfg.request &&
          StringHelper.capitalize(
            (_a4 = cfg.request) == null ? void 0 : _a4.type,
          ) + " failed") ||
        "Crud Manager request failed",
    );
    Object.assign(this, cfg);
    this.action = (_b = this.request) == null ? void 0 : _b.type;
  }
};
var storeSortFn = function (lhs, rhs, sortProperty) {
  if (lhs.store) {
    lhs = lhs.store;
  }
  if (rhs.store) {
    rhs = rhs.store;
  }
  lhs = lhs[sortProperty] || 0;
  rhs = rhs[sortProperty] || 0;
  return lhs < rhs ? -1 : lhs > rhs ? 1 : 0;
};
var storeLoadSortFn = function (lhs, rhs) {
  return storeSortFn(lhs, rhs, "loadPriority");
};
var storeSyncSortFn = function (lhs, rhs) {
  return storeSortFn(lhs, rhs, "syncPriority");
};
var AbstractCrudManagerMixin_default = (Target) => {
  var _a4;
  Target.$$meta = Target.$meta;
  const mixins = [];
  if (!Target.isEvents) {
    mixins.push(Events_default);
  }
  if (!Target.isDelayable) {
    mixins.push(Delayable_default);
  }
  mixins.push(AbstractCrudManagerValidation_default);
  return (
    (_a4 = class extends (Target || Base).mixin(...mixins) {
      /**
       * Fires before server response gets applied to the stores. Return `false` to prevent data applying.
       * This event can be used for server data preprocessing. To achieve it user can modify the `response` object.
       * @event beforeResponseApply
       * @param {Scheduler.crud.AbstractCrudManager} source The CRUD manager.
       * @param {'sync'|'load'} requestType The request type (`sync` or `load`).
       * @param {Object} response The decoded server response object.
       * @preventable
       */
      /**
       * Fires before loaded data get applied to the stores. Return `false` to prevent data applying.
       * This event can be used for server data preprocessing. To achieve it user can modify the `response` object.
       * @event beforeLoadApply
       * @param {Scheduler.crud.AbstractCrudManager} source The CRUD manager.
       * @param {Object} response The decoded server response object.
       * @param {Object} options Options provided to the {@link #function-load} method.
       * @preventable
       */
      /**
       * Fires before sync response data get applied to the stores. Return `false` to prevent data applying.
       * This event can be used for server data preprocessing. To achieve it user can modify the `response` object.
       * @event beforeSyncApply
       * @param {Scheduler.crud.AbstractCrudManager} source The CRUD manager.
       * @param {Object} response The decoded server response object.
       * @preventable
       */
      static get $name() {
        return "AbstractCrudManagerMixin";
      }
      //region Default config
      static get defaultConfig() {
        return {
          /**
           * The server revision stamp.
           * The _revision stamp_ is a number which should be incremented after each server-side change.
           * This property reflects the current version of the data retrieved from the server and gets updated
           * after each {@link #function-load} and {@link #function-sync} call.
           * @property {Number}
           * @readonly
           * @category CRUD
           */
          crudRevision: null,
          /**
           * A list of registered stores whose server communication will be collected into a single batch.
           * Each store is represented by a _store descriptor_.
           * @member {CrudManagerStoreDescriptor[]} crudStores
           * @category CRUD
           */
          /**
           * Sets the list of stores controlled by the CRUD manager.
           *
           * When adding a store to the CrudManager, make sure the server response format is correct for `load`
           * and `sync` requests. Learn more in the
           * [Working with data](#Scheduler/guides/data/crud_manager.md#loading-data) guide.
           *
           * Store can be provided by itself, its storeId or as a _store descriptor_.
           * @config {Core.data.Store[]|String[]|CrudManagerStoreDescriptor[]}
           * @category CRUD
           */
          crudStores: [],
          /**
           * Name of a store property to retrieve store identifiers from. Make sure you have an instance of a
           * store to use it by id. Store identifier is used as a container name holding corresponding store data
           * while transferring them to/from the server. By default, `storeId` property is used. And in case a
           * container identifier has to differ this config can be used:
           *
           * ```javascript
           * class CatStore extends Store {
           *     static configurable = {
           *         // store id is "meow" but for sending/receiving store data
           *         // we want to have "cats" container in JSON, so we create a new property "storeIdForCrud"
           *         id             : 'meow',
           *         storeIdForCrud : 'cats'
           *     }
           * });
           *
           * // create an instance to use a store by id
           * new CatStore();
           *
           * class MyCrudManager extends CrudManager {
           *     ...
           *     crudStores           : ['meow'],
           *     // crud manager will get store identifier from "storeIdForCrud" property
           *     storeIdProperty  : 'storeIdForCrud'
           * });
           * ```
           * The `storeIdProperty` property can also be specified directly on a store:
           *
           * ```javascript
           * class CatStore extends Store {
           *     static configurable = {
           *         // storeId is "meow" but for sending/receiving store data
           *         // we want to have "cats" container in JSON
           *         id              : 'meow',
           *         // so we create a new property "storeIdForCrud"..
           *         storeIdForCrud  : 'cats',
           *         // and point CrudManager to use it as the store identifier source
           *         storeIdProperty  : 'storeIdForCrud'
           *     }
           * });
           *
           * class DogStore extends Store {
           *     static configurable = {
           *         // storeId is "dogs" and it will be used as a container name for the store data
           *         storeId : 'dogs',
           *         // id is set to get a store by identifier
           *         id      : 'dogs'
           *     }
           * });
           *
           * // create an instance to use a store by id
           * new CatStore();
           * new DogStore();
           *
           * class MyCrudManager extends CrudManager {
           *     ...
           *     crudStores : ['meow', 'dogs']
           * });
           * ```
           * @config {String}
           * @category CRUD
           */
          storeIdProperty: "storeId",
          crudFilterParam: "filter",
          /**
           * Sends request to the server.
           * @function sendRequest
           * @param {Object} request The request to send. An object having following properties:
           * @param {'load'|'sync'} request.type Request type, can be either `load` or `sync`
           * @param {String} request.data {@link #function-encode Encoded} request.
           * @param {Function} request.success Callback to be started on successful request transferring
           * @param {Function} request.failure Callback to be started on request transfer failure
           * @param {Object} request.thisObj `this` reference for the above `success` and `failure` callbacks
           * @returns {Promise} The request promise.
           * @abstract
           */
          /**
           * Cancels request to the server.
           * @function cancelRequest
           * @param {Promise} promise The request promise to cancel (a value returned by corresponding
           * {@link #function-sendRequest} call).
           * @param {Function} reject Reject handle of the corresponding promise
           * @abstract
           */
          /**
           * Encodes request to the server.
           * @function encode
           * @param {Object} request The request to encode.
           * @returns {String} The encoded request.
           * @abstract
           */
          /**
           * Decodes response from the server.
           * @function decode
           * @param {String} response The response to decode.
           * @returns {Object} The decoded response.
           * @abstract
           */
          transport: {},
          /**
           * When `true` forces the CRUD manager to process responses depending on their `type` attribute.
           * So `load` request may be responded with `sync` response for example.
           * Can be used for smart server logic allowing the server to decide when it's better to respond with a
           * complete data set (`load` response) or it's enough to return just a delta (`sync` response).
           * @config {Boolean}
           * @default
           * @category CRUD
           */
          trackResponseType: false,
          /**
           * When `true` the Crud Manager does not require all updated and removed records to be mentioned in the
           * *sync* response. In this case response should include only server side changes.
           *
           * **Please note that added records should still be mentioned in response to provide real identifier
           * instead of the phantom one.**
           * @config {Boolean}
           * @default
           * @category CRUD
           */
          supportShortSyncResponse: true,
          /**
           * Field name to be used to transfer a phantom record identifier.
           * @config {String}
           * @default
           * @category CRUD
           */
          phantomIdField: "$PhantomId",
          /**
           * Field name to be used to transfer a phantom parent record identifier.
           * @config {String}
           * @default
           * @category CRUD
           */
          phantomParentIdField: "$PhantomParentId",
          /**
           * Specify `true` to automatically call {@link #function-load} method on the next frame after creation.
           *
           * Called on the next frame to allow a Scheduler (or similar) linked to a standalone CrudManager to
           * register its stores before loading starts.
           *
           * @config {Boolean}
           * @default
           * @category CRUD
           */
          autoLoad: false,
          /**
           * The timeout in milliseconds to wait before persisting changes to the server.
           * Used when {@link #config-autoSync} is set to `true`.
           * @config {Number}
           * @default
           * @category CRUD
           */
          autoSyncTimeout: 100,
          /**
           * `true` to automatically persist store changes after edits are made in any of the stores monitored.
           * Please note that sync request will not be invoked immediately but only after
           * {@link #config-autoSyncTimeout} interval.
           * @config {Boolean}
           * @default
           * @category CRUD
           */
          autoSync: false,
          /**
           * `True` to reset identifiers (defined by `idField` config) of phantom records before submitting them
           * to the server.
           * @config {Boolean}
           * @default
           * @category CRUD
           */
          resetIdsBeforeSync: true,
          /**
           * @member {CrudManagerStoreDescriptor[]} syncApplySequence
           * An array of stores presenting an alternative sync responses apply order.
           * Each store is represented by a _store descriptor_.
           * @category CRUD
           */
          /**
           * An array of store identifiers sets an alternative sync responses apply order.
           * By default, the order in which sync responses are applied to the stores is the same as they
           * registered in. But in case of some tricky dependencies between stores this order can be changed:
           *
           *```javascript
           * class MyCrudManager extends CrudManager {
           *     // register stores (will be loaded in this order: 'store1' then 'store2' and finally 'store3')
           *     crudStores : ['store1', 'store2', 'store3'],
           *     // but we apply changes from server to them in an opposite order
           *     syncApplySequence : ['store3', 'store2', 'store1']
           * });
           *```
           * @config {String[]}
           * @category CRUD
           */
          syncApplySequence: [],
          orderedCrudStores: [],
          /**
           * `true` to write all fields from the record to the server.
           * If set to `false` it will only send the fields that were modified.
           * Note that any fields that have {@link Core/data/field/DataField#config-persist} set to `false` will
           * still be ignored and fields having {@link Core/data/field/DataField#config-alwaysWrite} set to `true`
           * will always be included.
           * @config {Boolean}
           * @default
           * @category CRUD
           */
          writeAllFields: false,
          crudIgnoreUpdates: 0,
          autoSyncSuspendCounter: 0,
          // Flag that shows if crud manager performed successful load request
          crudLoaded: false,
          applyingLoadResponse: false,
          applyingSyncResponse: false,
          callOnFunctions: true,
        };
      }
      get isCrudManager() {
        return true;
      }
      //endregion
      //region Init
      construct(config = {}) {
        this._requestId = 0;
        this.activeRequests = {};
        this.crudStoresIndex = {};
        super.construct(config);
      }
      afterConstruct() {
        super.afterConstruct();
        if (this.autoLoad) {
          this._autoLoadPromise = this.doAutoLoad();
        }
      }
      //endregion
      //region Configs
      get loadUrl() {
        var _a5, _b;
        return (_b = (_a5 = this.transport) == null ? void 0 : _a5.load) == null
          ? void 0
          : _b.url;
      }
      updateLoadUrl(url) {
        ObjectHelper.setPath(this, "transport.load.url", url);
      }
      get syncUrl() {
        var _a5, _b;
        return (_b = (_a5 = this.transport) == null ? void 0 : _a5.sync) == null
          ? void 0
          : _b.url;
      }
      updateSyncUrl(url) {
        ObjectHelper.setPath(this, "transport.sync.url", url);
      }
      //endregion
      //region Store descriptors & index
      /**
       * Returns a registered store descriptor.
       * @param {String|Core.data.Store} storeId The store identifier or registered store instance.
       * @returns {CrudManagerStoreDescriptor} The descriptor of the store.
       * @category CRUD
       */
      getStoreDescriptor(storeId) {
        if (!storeId) return null;
        if (storeId instanceof Store)
          return this.crudStores.find(
            (storeDesc) => storeDesc.store === storeId,
          );
        if (typeof storeId === "object")
          return this.crudStoresIndex[storeId.storeId];
        return (
          this.crudStoresIndex[storeId] ||
          this.getStoreDescriptor(Store.getStore(storeId))
        );
      }
      fillStoreDescriptor(descriptor) {
        const { store } = descriptor,
          { storeIdProperty = this.storeIdProperty, modelClass } = store;
        if (!descriptor.storeId) {
          descriptor.storeId = store[storeIdProperty] || store.id;
        }
        if (!descriptor.idField) {
          descriptor.idField = modelClass.idField;
        }
        if (!descriptor.phantomIdField) {
          descriptor.phantomIdField = modelClass.phantomIdField;
        }
        if (!descriptor.phantomParentIdField) {
          descriptor.phantomParentIdField = modelClass.phantomParentIdField;
        }
        if (!("writeAllFields" in descriptor)) {
          descriptor.writeAllFields = store.writeAllFields;
        }
        return descriptor;
      }
      updateCrudStoreIndex() {
        const crudStoresIndex = (this.crudStoresIndex = {});
        this.crudStores.forEach(
          (store) => store.storeId && (crudStoresIndex[store.storeId] = store),
        );
      }
      //endregion
      //region Store collection (add, remove, get & iterate)
      /**
       * Returns a registered store.
       * @param {String} storeId Store identifier.
       * @returns {Core.data.Store} Found store instance.
       * @category CRUD
       */
      getCrudStore(storeId) {
        const storeDescriptor = this.getStoreDescriptor(storeId);
        return storeDescriptor == null ? void 0 : storeDescriptor.store;
      }
      forEachCrudStore(fn2, thisObj = this) {
        if (!fn2) {
          throw new Error("Iterator function must be provided");
        }
        this.crudStores.every(
          (store) =>
            fn2.call(thisObj, store.store, store.storeId, store) !== false,
        );
      }
      set crudStores(stores2) {
        this._crudStores = [];
        this.addCrudStore(stores2);
        for (const store of this._crudStores) {
          store.loadPriority = store.syncPriority = 0;
        }
      }
      get crudStores() {
        return this._crudStores;
      }
      get orderedCrudStores() {
        return this._orderedCrudStores;
      }
      set orderedCrudStores(stores2) {
        return (this._orderedCrudStores = stores2);
      }
      set syncApplySequence(stores2) {
        this._syncApplySequence = [];
        this.addStoreToApplySequence(stores2);
      }
      get syncApplySequence() {
        return this._syncApplySequence;
      }
      internalAddCrudStore(store) {
        const me = this;
        let storeInfo;
        if (store instanceof Store) {
          storeInfo = { store };
        } else if (typeof store === "object") {
          if (!store.store) {
            store = {
              storeId: store.id,
              store: new Store(store),
            };
          }
          storeInfo = store;
        } else {
          storeInfo = { store: Store.getStore(store) };
        }
        me.fillStoreDescriptor(storeInfo);
        store = storeInfo.store;
        if (store.setCrudManager) {
          store.setCrudManager(me);
        } else {
          store.crudManager = me;
        }
        store.pageSize = null;
        if (me.loadUrl || me.syncUrl) {
          store.autoCommit = false;
          store.autoLoad = false;
          if (
            store.createUrl ||
            store.updateUrl ||
            store.deleteUrl ||
            store.readUrl
          ) {
            console.warn(
              "You have configured an URL on a Store that is handled by a CrudManager that is also configured with an URL. The Store URL's should be removed.",
            );
          }
        }
        me.bindCrudStoreListeners(store);
        return storeInfo;
      }
      /**
       * Adds a store to the collection.
       *
       *```javascript
       * // append stores to the end of collection
       * crudManager.addCrudStore([
       *     store1,
       *     // storeId
       *     'bar',
       *     // store descriptor
       *     {
       *         storeId : 'foo',
       *         store   : store3
       *     },
       *     {
       *         storeId         : 'bar',
       *         store           : store4,
       *         // to write all fields of modified records
       *         writeAllFields  : true
       *     }
       * ]);
       *```
       *
       * **Note:** Order in which stores are kept in the collection is very essential sometimes.
       * Exactly in this order the loaded data will be put into each store.
       *
       * When adding a store to the CrudManager, make sure the server response format is correct for `load` and `sync`
       * requests. Learn more in the [Working with data](#Scheduler/guides/data/crud_manager.md#loading-data) guide.
       *
       * @param {Core.data.Store|String|CrudManagerStoreDescriptor|Core.data.Store[]|String[]|CrudManagerStoreDescriptor[]} store
       * A store or list of stores. Each store might be specified by its instance, `storeId` or _descriptor_.
       * @param {Number} [position] The relative position of the store. If `fromStore` is specified the position
       * will be taken relative to it. If not specified then store(s) will be appended to the end of collection.
       * Otherwise, it will be just a position in stores collection.
       *
       * ```javascript
       * // insert stores store4, store5 to the start of collection
       * crudManager.addCrudStore([ store4, store5 ], 0);
       * ```
       *
       * @param {String|Core.data.Store|CrudManagerStoreDescriptor} [fromStore] The store relative to which position
       * should be calculated. Can be defined as a store identifier, instance or descriptor (the result of
       * {@link #function-getStoreDescriptor} call).
       *
       * ```javascript
       * // insert store6 just before a store having storeId equal to 'foo'
       * crudManager.addCrudStore(store6, 0, 'foo');
       *
       * // insert store7 just after store3 store
       * crudManager.addCrudStore(store7, 1, store3);
       * ```
       * @category CRUD
       */
      addCrudStore(store, position, fromStore) {
        store = ArrayHelper.asArray(store);
        if (!(store == null ? void 0 : store.length)) {
          return;
        }
        const me = this,
          stores2 = store.map(me.internalAddCrudStore, me);
        if (typeof position === "undefined") {
          me.crudStores.push(...stores2);
        } else {
          if (fromStore) {
            if (fromStore instanceof Store || typeof fromStore !== "object")
              fromStore = me.getStoreDescriptor(fromStore);
            position += me.crudStores.indexOf(fromStore);
          }
          me.crudStores.splice(position, 0, ...stores2);
        }
        me.orderedCrudStores.push(...stores2);
        me.updateCrudStoreIndex();
      }
      // Adds configured scheduler stores to the store collection ensuring correct order
      // unless they're already registered.
      addPrioritizedStore(store) {
        const me = this;
        if (!me.hasCrudStore(store)) {
          me.addCrudStore(
            store,
            ArrayHelper.findInsertionIndex(
              store,
              me.crudStores,
              storeLoadSortFn,
            ),
          );
        }
        if (!me.hasApplySequenceStore(store)) {
          me.addStoreToApplySequence(
            store,
            ArrayHelper.findInsertionIndex(
              store,
              me.syncApplySequence,
              storeSyncSortFn,
            ),
          );
        }
      }
      hasCrudStore(store) {
        var _a5;
        return (_a5 = this.crudStores) == null
          ? void 0
          : _a5.some(
              (s) => s === store || s.store === store || s.storeId === store,
            );
      }
      /**
       * Removes a store from collection. If the store was registered in alternative sync sequence list
       * it will be removed from there as well.
       *
       * ```javascript
       * // remove store having storeId equal to "foo"
       * crudManager.removeCrudStore("foo");
       *
       * // remove store3
       * crudManager.removeCrudStore(store3);
       * ```
       *
       * @param {CrudManagerStoreDescriptor|String|Core.data.Store} store The store to remove. Either the store
       * descriptor, store identifier or store itself.
       * @category CRUD
       */
      removeCrudStore(store) {
        const me = this,
          stores2 = me.crudStores,
          foundStore = stores2.find(
            (s) => s === store || s.store === store || s.storeId === store,
          );
        if (foundStore) {
          me.unbindCrudStoreListeners(foundStore.store);
          delete me.crudStoresIndex[foundStore.storeId];
          ArrayHelper.remove(stores2, foundStore);
          if (me.syncApplySequence) {
            me.removeStoreFromApplySequence(store);
          }
        } else {
          throw new Error("Store not found in stores collection");
        }
      }
      //endregion
      //region Store listeners
      bindCrudStoreListeners(store) {
        store.ion({
          name: store.id,
          // When a tentatively added record gets confirmed as permanent, this signals a change
          addConfirmed: "onCrudStoreChange",
          change: "onCrudStoreChange",
          destroy: "onCrudStoreDestroy",
          thisObj: this,
        });
      }
      unbindCrudStoreListeners(store) {
        this.detachListeners(store.id);
      }
      //endregion
      //region Apply sequence
      /**
       * Adds a store to the alternative sync responses apply sequence.
       * By default, the order in which sync responses are applied to the stores is the same as they registered in.
       * But this order can be changes either on construction step using {@link #config-syncApplySequence} option
       * or by calling this method.
       *
       * **Please note**, that if the sequence was not initialized before this method call then
       * you will have to do it yourself like this for example:
       *
       * ```javascript
       * // alternative sequence was not set for this crud manager
       * // so let's fill it with existing stores keeping the same order
       * crudManager.addStoreToApplySequence(crudManager.crudStores);
       *
       * // and now we can add our new store
       *
       * // we will load its data last
       * crudManager.addCrudStore(someNewStore);
       * // but changes to it will be applied first
       * crudManager.addStoreToApplySequence(someNewStore, 0);
       * ```
       * add registered stores to the sequence along with the store(s) you want to add
       *
       * @param {Core.data.Store|CrudManagerStoreDescriptor|Core.data.Store[]|CrudManagerStoreDescriptor[]} store The
       * store to add or its _descriptor_ (or array of stores or descriptors).
       * @param {Number} [position] The relative position of the store. If `fromStore` is specified the position
       * will be taken relative to it. If not specified then store(s) will be appended to the end of collection.
       * Otherwise, it will be just a position in stores collection.
       *
       * ```javascript
       * // insert stores store4, store5 to the start of sequence
       * crudManager.addStoreToApplySequence([ store4, store5 ], 0);
       * ```
       * @param {String|Core.data.Store|CrudManagerStoreDescriptor} [fromStore] The store relative to which position
       * should be calculated. Can be defined as a store identifier, instance or its descriptor (the result of
       * {@link #function-getStoreDescriptor} call).
       *
       * ```javascript
       * // insert store6 just before a store having storeId equal to 'foo'
       * crudManager.addStoreToApplySequence(store6, 0, 'foo');
       *
       * // insert store7 just after store3 store
       * crudManager.addStoreToApplySequence(store7, 1, store3);
       * ```
       * @category CRUD
       */
      addStoreToApplySequence(store, position, fromStore) {
        if (!store) {
          return;
        }
        store = ArrayHelper.asArray(store);
        const me = this,
          data = store.reduce((collection, store2) => {
            const s = me.getStoreDescriptor(store2);
            s && collection.push(s);
            return collection;
          }, []);
        if (typeof position === "undefined") {
          me.syncApplySequence.push(...data);
        } else {
          let pos = position;
          if (fromStore) {
            if (fromStore instanceof Store || typeof fromStore !== "object")
              fromStore = me.getStoreDescriptor(fromStore);
            pos += me.syncApplySequence.indexOf(fromStore);
          }
          me.syncApplySequence.splice(pos, 0, ...data);
        }
        const sequenceKeys = me.syncApplySequence.map(({ storeId }) => storeId);
        me.orderedCrudStores = [...me.syncApplySequence];
        me.crudStores.forEach((storeDesc) => {
          if (!sequenceKeys.includes(storeDesc.storeId)) {
            me.orderedCrudStores.push(storeDesc);
          }
        });
      }
      /**
       * Removes a store from the alternative sync sequence.
       *
       * ```javascript
       * // remove store having storeId equal to "foo"
       * crudManager.removeStoreFromApplySequence("foo");
       * ```
       *
       * @param {CrudManagerStoreDescriptor|String|Core.data.Store} store The store to remove. Either the store
       * descriptor, store identifier or store itself.
       * @category CRUD
       */
      removeStoreFromApplySequence(store) {
        const index = this.syncApplySequence.findIndex(
          (s) => s === store || s.store === store || s.storeId === store,
        );
        if (index > -1) {
          this.syncApplySequence.splice(index, 1);
          this.orderedCrudStores.splice(index, 1);
        }
      }
      hasApplySequenceStore(store) {
        return this.syncApplySequence.some(
          (s) => s === store || s.store === store || s.storeId === store,
        );
      }
      //endregion
      //region Events
      // Remove stores that are destroyed, to not try and apply response changes etc. to them
      onCrudStoreDestroy({ source: store }) {
        this.removeCrudStore(store);
      }
      onCrudStoreChange(event) {
        const me = this;
        if (me.crudIgnoreUpdates) {
          return;
        }
        if (me.crudStoreHasChanges(event == null ? void 0 : event.source)) {
          me.trigger("hasChanges");
          if (me.autoSync) {
            me.scheduleAutoSync();
          }
        } else {
          me.trigger("noChanges");
        }
      }
      /**
       * Suspends automatic sync upon store changes. Can be called multiple times (it uses an internal counter).
       * @category CRUD
       */
      suspendAutoSync() {
        this.autoSyncSuspendCounter++;
      }
      /**
       * Resumes automatic sync upon store changes. Will schedule a sync if the internal counter is 0.
       * @param {Boolean} [doSync=true] Pass `true` to schedule a sync after resuming (if there are pending
       * changes) and `false` to not persist the changes.
       * @category CRUD
       */
      resumeAutoSync(doSync = true) {
        const me = this;
        me.autoSyncSuspendCounter--;
        if (me.autoSyncSuspendCounter <= 0) {
          me.autoSyncSuspendCounter = 0;
          if (doSync && me.autoSync && me.crudStoreHasChanges()) {
            me.scheduleAutoSync();
          }
        }
      }
      get isAutoSyncSuspended() {
        return this.autoSyncSuspendCounter > 0;
      }
      scheduleAutoSync() {
        const me = this;
        if (!me.hasTimeout("autoSync") && !me.isAutoSyncSuspended) {
          me.setTimeout({
            name: "autoSync",
            fn: () => {
              me.sync().catch((error) => {});
            },
            delay: me.autoSyncTimeout,
          });
        }
      }
      async triggerFailedRequestEvents(
        request,
        response,
        responseText,
        fetchOptions,
      ) {
        const { options, type: requestType } = request;
        this.trigger("requestFail", {
          requestType,
          response,
          responseText,
          responseOptions: fetchOptions,
        });
        this.trigger(requestType + "Fail", {
          response,
          responseOptions: fetchOptions,
          responseText,
          options,
        });
      }
      async internalOnResponse(request, responseText, fetchOptions) {
        const me = this,
          response = responseText ? me.decode(responseText) : null,
          { options, type: requestType } = request;
        if (responseText && !response) {
          console.error("Failed to parse response: " + responseText);
        }
        if (
          !response ||
          (me.skipSuccessProperty
            ? response.success === false
            : !response.success)
        ) {
          me.triggerFailedRequestEvents(
            request,
            response,
            responseText,
            fetchOptions,
          );
        } else if (
          me.trigger("beforeResponseApply", { requestType, response }) !==
            false &&
          me.trigger(`before${StringHelper.capitalize(requestType)}Apply`, {
            response,
            options,
          }) !== false
        ) {
          me.crudRevision = response.revision;
          await me.applyResponse(request, response, options);
          if (me.isDestroyed) {
            return;
          }
          me.trigger("requestDone", {
            requestType,
            response,
            responseOptions: fetchOptions,
          });
          me.trigger(requestType, {
            response,
            responseOptions: fetchOptions,
            options,
          });
          if (requestType === "load" || !me.crudStoreHasChanges()) {
            me.trigger("noChanges");
            if (requestType === "load") {
              me.emitCrudStoreEvents(request.pack.stores, "afterRequest");
            }
          }
        }
        return response;
      }
      //endregion
      //region Changes tracking
      /**
       * Suspends {@link #event-hasChanges} and {@link #event-noChanges} events.
       * @category CRUD
       */
      suspendChangeTracking() {
        this.crudIgnoreUpdates++;
      }
      /**
       * Resumes {@link #event-hasChanges} and {@link #event-noChanges} events. By default, it will check for changes
       * and if there are any, `hasChanges` or `noChanges` event will be triggered.
       * @param {Boolean} [skipChangeCheck]
       * @category CRUD
       */
      resumeChangeTracking(skipChangeCheck) {
        if (
          this.crudIgnoreUpdates &&
          !--this.crudIgnoreUpdates &&
          !skipChangeCheck
        ) {
          this.onCrudStoreChange();
        }
      }
      /**
       * Returns `true` if changes tracking is suspended
       * @property {Boolean}
       * @readonly
       * @category CRUD
       */
      get isChangeTrackingSuspended() {
        return this.crudIgnoreUpdates > 0;
      }
      /**
       * Returns `true` if any of registered stores (or some particular store) has non persisted changes.
       *
       * ```javascript
       * // if we have any unsaved changes
       * if (crudManager.crudStoreHasChanges()) {
       *     // persist them
       *     crudManager.sync();
       * // otherwise
       * } else {
       *     alert("There are no unsaved changes...");
       * }
       * ```
       *
       * @param {String|Core.data.Store} [storeId] The store identifier or store instance to check changes for.
       * If not specified then will check changes for all of the registered stores.
       * @returns {Boolean} `true` if there are not persisted changes.
       * @category CRUD
       */
      crudStoreHasChanges(storeId) {
        return storeId
          ? this.isCrudStoreDirty(this.getCrudStore(storeId))
          : this.crudStores.some((config) =>
              this.isCrudStoreDirty(config.store),
            );
      }
      isCrudStoreDirty(store) {
        return Boolean(store.changes);
      }
      //endregion
      //region Load
      doAutoLoad() {
        return this.load().catch((error) => {});
      }
      emitCrudStoreEvents(stores2, eventName, eventParams) {
        const event = { action: "read" + eventName, ...eventParams };
        for (const store of this.crudStores) {
          if (stores2.includes(store.storeId)) {
            store.store.trigger(eventName, event);
          }
        }
      }
      getLoadPackage(options) {
        const pack = {
            type: "load",
            requestId: this.requestId,
          },
          stores2 = this.crudStores,
          optionsCopy = Object.assign({}, options);
        delete optionsCopy.request;
        pack.stores = stores2.map((store) => {
          var _a5;
          const opts =
              optionsCopy == null ? void 0 : optionsCopy[store.storeId],
            pageSize =
              store.pageSize ||
              ((_a5 = store.store) == null ? void 0 : _a5.pageSize);
          if (opts || pageSize) {
            const params = Object.assign(
              {
                storeId: store.storeId,
                page: 1,
              },
              opts,
            );
            if (pageSize) {
              params.pageSize = pageSize;
            }
            store.currentPage = params.page;
            if (opts) {
              delete optionsCopy[store.storeId];
            }
            return params;
          }
          return store.storeId;
        });
        Object.assign(pack, optionsCopy);
        return pack;
      }
      loadCrudStore(store, data, options) {
        const rows = data == null ? void 0 : data.rows;
        if (
          (options == null ? void 0 : options.append) ||
          (data == null ? void 0 : data.append)
        ) {
          store.add(rows, false, { clean: true });
        } else {
          store.data = rows;
        }
        store.trigger("load", { data: rows });
      }
      loadDataToCrudStore(storeDesc, data, options) {
        const store = storeDesc.store,
          rows = data == null ? void 0 : data.rows;
        store.__loading = true;
        if (rows) {
          this.loadCrudStore(store, data, options, storeDesc);
        }
        store.__loading = false;
      }
      /**
       * Loads data to the Crud Manager
       * @param {Object} response A simple object representing the data.
       * The object structure matches the decoded `load` response structure:
       *
       * ```js
       * // load static data into crudManager
       * crudManager.loadCrudManagerData({
       *     success   : true,
       *     resources : {
       *         rows : [
       *             { id : 1, name : 'John' },
       *             { id : 2, name : 'Abby' }
       *         ]
       *     }
       * });
       * ```
       * @param {Object} [options] Extra data loading options.
       * @category CRUD
       */
      loadCrudManagerData(response, options = {}) {
        const me = this;
        me.trigger("beforeLoadCrudManagerData");
        me.suspendChangeTracking();
        me.crudStores.forEach((storeDesc) => {
          const storeId = storeDesc.storeId,
            data = response[storeId];
          if (data) {
            me.loadDataToCrudStore(storeDesc, data, options[storeId]);
          }
        });
        me.resumeChangeTracking(true);
        me.trigger("loadCrudManagerData");
      }
      /**
       * Returns true if the crud manager is currently loading data
       * @property {Boolean}
       * @readonly
       * @category CRUD
       */
      get isCrudManagerLoading() {
        return Boolean(this.activeRequests.load || this.applyingLoadResponse);
      }
      /**
       * Returns true if the crud manager is currently syncing data
       * @property {Boolean}
       * @readonly
       * @category CRUD
       */
      get isCrudManagerSyncing() {
        return Boolean(this.activeRequests.sync || this.applyingSyncResponse);
      }
      get isLoadingOrSyncing() {
        return Boolean(this.isCrudManagerLoading || this.isCrudManagerSyncing);
      }
      /**
       * Loads data to the stores registered in the crud manager. For example:
       *
       * ```javascript
       * crudManager.load(
       *     // here are request parameters
       *     {
       *         store1 : { append : true, page : 3, smth : 'foo' },
       *         store2 : { page : 2, bar : '!!!' }
       *     }
       * ).then(
       *     () => alert('OMG! It works!'),
       *     ({ response, cancelled }) => console.log(`Error: ${cancelled ? 'Cancelled' : response.message}`)
       * );
       * ```
       *
       * ** Note: ** If there is an incomplete load request in progress then system will try to cancel it by calling {@link #function-cancelRequest}.
       * @param {Object|String} [options] The request parameters or a URL.
       * @param {Object} [options.request] An object which contains options to merge
       * into the options which are passed to {@link Scheduler/crud/transport/AjaxTransport#function-sendRequest}.
       * ```javascript
       * {
       *     store1 : { page : 3, append : true, smth : 'foo' },
       *     store2 : { page : 2, bar : '!!!' },
       *     request : {
       *         params : {
       *             startDate : '2021-01-01'
       *         }
       *     }
       * },
       * ```
       *
       * Omitting request arg:
       * ```javascript
       * crudManager.load().then(
       *     () => alert('OMG! It works!'),
       *     ({ response, cancelled }) => console.log(`Error: ${cancelled ? 'Cancelled' : response.message}`)
       * );
       * ```
       *
       * When presented it should be an object where keys are store Ids and values are, in turn, objects
       * of parameters related to the corresponding store. These parameters will be transferred in each
       * store's entry in the `stores` property of the POST data.
       *
       * Additionally, for flat stores `append: true` can be specified to add loaded records to the existing records,
       * default is to remove corresponding store's existing records first.
       * **Please note** that for delta loading you can also use an {@link #config-trackResponseType alternative approach}.
       * @param {'sync'|'load'} [options.request.type] The request type. Either `load` or `sync`.
       * @param {String} [options.request.url] The URL for the request. Overrides the URL defined in the `transport`
       * object
       * @param {String} [options.request.data] The encoded _Crud Manager_ request data.
       * @param {Object} [options.request.params] An object specifying extra HTTP params to send with the request.
       * @param {Function} [options.request.success] A function to be started on successful request transferring.
       * @param {String} [options.request.success.rawResponse] `Response` object returned by the
       * [fetch api](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API).
       * @param {Function} [options.request.failure] A function to be started on request transfer failure.
       * @param {String} [options.request.failure.rawResponse] `Response` object returned by the
       * [fetch api](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API).
       * @param {Object} [options.request.thisObj] `this` reference for the above `success` and `failure` functions.
       * @returns {Promise} Promise, which is resolved if request was successful.
       * Both the resolve and reject functions are passed a `state` object. State object has following structure:
       *
       * ```
       * {
       *     cancelled       : Boolean, // **optional** flag, which is present when promise was rejected
       *     rawResponse     : String,  // raw response from ajax request, either response xml or text
       *     rawResponseText : String,  // raw response text as String from ajax request
       *     response        : Object,  // processed response in form of object
       *     options         : Object   // options, passed to load request
       * }
       * ```
       *
       * If promise was rejected by {@link #event-beforeLoad} event, `state` object will have the following structure:
       *
       * ```
       * {
       *     cancelled : true
       * }
       * ```
       * @category CRUD
       * @async
       */
      load(options) {
        if (typeof options === "string") {
          options = {
            request: {
              url: options,
            },
          };
        }
        const me = this,
          pack = me.getLoadPackage(options);
        me._autoLoadPromise = null;
        return new Promise((resolve, reject) => {
          if (me.trigger("beforeLoad", { pack }) !== false) {
            const { load } = me.activeRequests;
            if (load) {
              me.cancelRequest(load.desc, load.reject);
              me.trigger("loadCanceled", { pack });
            }
            const request = Objects.assign(
              {
                id: pack.requestId,
                data: me.encode(pack),
                type: "load",
                success: me.onCrudRequestSuccess,
                failure: me.onCrudRequestFailure,
                thisObj: me,
              },
              options == null ? void 0 : options.request,
            );
            me.activeRequests.load = {
              type: "load",
              options,
              pack,
              resolve,
              reject(...args) {
                request.success = request.failure = null;
                reject(...args);
              },
              id: pack.requestId,
              desc: me.sendRequest(request),
            };
            me.emitCrudStoreEvents(pack.stores, "loadStart");
            me.trigger("loadStart", { pack });
          } else {
            me.trigger("loadCanceled", { pack });
            reject({ cancelled: true });
          }
        });
      }
      getActiveCrudManagerRequest(requestType) {
        let request = this.activeRequests[requestType];
        if (!request && this.trackResponseType) {
          request = Object.values(this.activeRequests)[0];
        }
        return request;
      }
      //endregion
      //region Changes (prepare, process, get)
      prepareAddedRecordData(record, storeInfo) {
        const me = this,
          { store } = storeInfo,
          { isTree } = store,
          phantomIdField = storeInfo.phantomIdField || me.phantomIdField,
          phantomParentIdField =
            storeInfo.phantomParentIdField || me.phantomParentIdField,
          subStoreFields = store.modelClass.allFields.filter(
            (field2) => field2.subStore,
          ),
          cls2 = record.constructor,
          data = Object.assign(record.persistableData, {
            [phantomIdField]: record.id,
          });
        if (isTree) {
          const { parent } = record;
          if (parent && !parent.isRoot && parent.isPhantom) {
            data[phantomParentIdField] = parent.id;
          }
        }
        if (me.resetIdsBeforeSync) {
          ObjectHelper.deletePath(data, cls2.idField);
        }
        subStoreFields.forEach((field2) => {
          const subStore = record.get(field2.name);
          if (subStore.allCount) {
            data[field2.dataSource] = {
              added: subStore
                .getRange()
                .map((record2) =>
                  me.prepareAddedRecordData(record2, { store: subStore }),
                ),
            };
          }
        });
        return data;
      }
      prepareAdded(list, storeInfo) {
        return list
          .filter((record) => record.isValid)
          .map((record) => this.prepareAddedRecordData(record, storeInfo));
      }
      prepareUpdated(list, storeInfo) {
        const { store } = storeInfo,
          { isTree } = store,
          writeAllFields =
            storeInfo.writeAllFields ||
            (storeInfo.writeAllFields !== false && this.writeAllFields),
          phantomParentIdField =
            storeInfo.phantomParentIdField || this.phantomParentIdField,
          subStoreFields = store.modelClass.allFields.filter(
            (field2) => field2.subStore,
          );
        if (storeInfo.store.tree) {
          const rootNode = storeInfo.store.rootNode;
          list = list.filter((record) => record !== rootNode);
        }
        return list
          .filter((record) => record.isValid)
          .reduce((data, record) => {
            let recordData;
            if (writeAllFields) {
              recordData = record.persistableData;
            } else {
              recordData = record.modificationDataToWrite;
            }
            if (isTree) {
              const { parent } = record;
              if (parent && !parent.isRoot && parent.isPhantom) {
                recordData[phantomParentIdField] = parent.id;
              }
            }
            subStoreFields.forEach((field2) => {
              const subStore = record.get(field2.name);
              recordData[field2.dataSource] = this.getCrudStoreChanges({
                store: subStore,
              });
            });
            if (!ObjectHelper.isEmpty(recordData)) {
              data.push(recordData);
            }
            return data;
          }, []);
      }
      prepareRemoved(list) {
        return list.map((record) => {
          const cls2 = record.constructor;
          return ObjectHelper.setPath({}, cls2.idField, record.id);
        });
      }
      getCrudStoreChanges(storeDescriptor) {
        const { store } = storeDescriptor;
        let {
            added = [],
            modified: updated = [],
            removed = [],
          } = store.changes || {},
          result;
        if (added.length) added = this.prepareAdded(added, storeDescriptor);
        if (updated.length)
          updated = this.prepareUpdated(updated, storeDescriptor);
        if (removed.length) removed = this.prepareRemoved(removed);
        if (added.length || updated.length || removed.length) {
          result = {};
          if (added.length) result.added = added;
          if (updated.length) result.updated = updated;
          if (removed.length) result.removed = removed;
        }
        return result;
      }
      getChangesetPackage() {
        const { changes } = this;
        return changes || this.forceSync
          ? {
              type: "sync",
              requestId: this.requestId,
              revision: this.crudRevision,
              ...changes,
            }
          : null;
      }
      //endregion
      //region Apply
      /**
       * Returns current changes as an object consisting of added/modified/removed arrays of records for every
       * managed store, keyed by each store's `id`. Returns `null` if no changes exist. Format:
       *
       * ```javascript
       * {
       *     resources : {
       *         added    : [{ name : 'New guy' }],
       *         modified : [{ id : 2, name : 'Mike' }],
       *         removed  : [{ id : 3 }]
       *     },
       *     events : {
       *         modified : [{  id : 12, name : 'Cool task' }]
       *     },
       *     ...
       * }
       * ```
       *
       * @property {Object}
       * @readonly
       * @category CRUD
       */
      get changes() {
        const data = {};
        this.crudStores.forEach((store) => {
          const changes = this.getCrudStoreChanges(store);
          if (changes) {
            data[store.storeId] = changes;
          }
        });
        return Object.keys(data).length > 0 ? data : null;
      }
      getRowsToApplyChangesTo({ store, storeId }, storeResponse, storePack) {
        var _a5, _b;
        const me = this,
          { modelClass } = store,
          idDataSource = modelClass.idField,
          { updated: requestUpdated, removed: requestRemoved } =
            storePack || {};
        let rows, removed, remote;
        if (storeResponse) {
          remote = true;
          const respondedIds = {};
          rows =
            ((_a5 = storeResponse.rows) == null ? void 0 : _a5.slice()) || [];
          removed =
            ((_b = storeResponse.removed) == null ? void 0 : _b.slice()) || [];
          [...rows, ...removed].forEach((responseRecord) => {
            const id = ObjectHelper.getPath(responseRecord, idDataSource);
            respondedIds[id] = true;
          });
          if (me.supportShortSyncResponse) {
            requestUpdated == null
              ? void 0
              : requestUpdated.forEach((data) => {
                  const id = ObjectHelper.getPath(data, idDataSource);
                  if (!respondedIds[id]) {
                    rows.push({ [idDataSource]: id });
                  }
                });
            requestRemoved == null
              ? void 0
              : requestRemoved.forEach((data) => {
                  const id = ObjectHelper.getPath(data, idDataSource);
                  if (!respondedIds[id]) {
                    removed.push({ [idDataSource]: id });
                  }
                });
          }
        } else if (requestUpdated || requestRemoved) {
          remote = false;
          rows = requestUpdated;
          removed = requestRemoved;
        }
        rows = (rows == null ? void 0 : rows.length) ? rows : null;
        removed = (removed == null ? void 0 : removed.length) ? removed : null;
        return {
          rows,
          removed,
          remote,
        };
      }
      applyChangesToStore(storeDesc, storeResponse, storePack) {
        var _a5;
        const me = this,
          phantomIdField = storeDesc.phantomIdField || me.phantomIdField,
          { store } = storeDesc,
          idField = store.modelClass.getFieldDataSource("id"),
          subStoreFields = store.modelClass.allFields.filter(
            (field2) => field2.subStore,
          ),
          { rows, removed, remote } = me.getRowsToApplyChangesTo(
            storeDesc,
            storeResponse,
            storePack,
          ),
          added = [],
          updated = [];
        if (rows) {
          for (const data of rows) {
            if (
              store.getById(
                (_a5 = data[phantomIdField]) != null ? _a5 : data[idField],
              )
            ) {
              updated.push(data);
            } else {
              added.push(data);
            }
          }
        }
        const extraLogEntries = [];
        if (updated.length && subStoreFields.length) {
          updated.forEach((updateData) => {
            var _a6, _b, _c;
            const record = store.getById(
                (_a6 = updateData[phantomIdField]) != null
                  ? _a6
                  : updateData[idField],
              ),
              recordRequest =
                ((_b = storePack.added) == null
                  ? void 0
                  : _b.find(
                      (t) => t[phantomIdField] == updateData[phantomIdField],
                    )) ||
                ((_c = storePack.updated) == null
                  ? void 0
                  : _c.find((t) => t[idField] == updateData[idField]));
            const extraLogInfo = {};
            subStoreFields.forEach((field2) => {
              const store2 = record.get(field2.name);
              me.applyChangesToStore(
                { store: store2 },
                updateData[field2.dataSource],
                recordRequest == null
                  ? void 0
                  : recordRequest[field2.dataSource],
              );
              extraLogInfo[field2.dataSource] = "foo";
              delete updateData[field2.dataSource];
            });
            extraLogEntries.push([record, extraLogInfo]);
          });
        }
        const log = store.applyChangeset(
          { removed, added, updated },
          null,
          phantomIdField,
          remote,
          true,
        );
        extraLogEntries.forEach(([record, logEntry]) =>
          Object.assign(log.get(record.id), logEntry),
        );
        return log;
      }
      applySyncResponse(response, request) {
        var _a5;
        const me = this,
          stores2 = me.orderedCrudStores;
        me.applyingChangeset = me.applyingSyncResponse = true;
        me.suspendChangeTracking();
        for (const store of stores2) {
          me.applyChangesToStore(
            store,
            response[store.storeId],
            (_a5 = request == null ? void 0 : request.pack) == null
              ? void 0
              : _a5[store.storeId],
          );
        }
        me.resumeChangeTracking(true);
        me.applyingChangeset = me.applyingSyncResponse = false;
      }
      applyLoadResponse(response, options) {
        this.applyingLoadResponse = true;
        this.loadCrudManagerData(response, options);
        this.applyingLoadResponse = false;
      }
      async applyResponse(request, response, options) {
        const me = this,
          responseType =
            (me.trackResponseType && response.type) || request.type;
        switch (responseType) {
          case "load":
            if (me.validateResponse) {
              me.validateLoadResponse(response);
            }
            me.applyLoadResponse(response, options);
            break;
          case "sync":
            if (me.validateResponse) {
              me.validateSyncResponse(response, request);
            }
            me.applySyncResponse(response, request);
            break;
        }
      }
      /**
       * Applies a set of changes, as an object keyed by store id, to the affected stores. This function is intended
       * to use in apps that handle their own data syncing, it is not needed when using the CrudManager approach.
       *
       * Example of a changeset:
       * ```javascript
       * project.applyChangeset({
       *     events : {
       *         added : [
       *             { id : 10, name : 'Event 10', startDate : '2022-06-07' }
       *         ],
       *         updated : [
       *             { id : 5, name : 'Changed' }
       *         ],
       *         removed : [
       *             { id : 1 }
       *         ]
       *     },
       *     resources : { ... },
       *     ...
       * });
       * ```
       *
       * Optionally accepts a `transformFn` to convert an incoming changeset to the expected format.
       * See {@link Core/data/Store#function-applyChangeset} for more details.
       *
       * @param {Object} changes Changeset to apply, an object keyed by store id where each value follows the
       * format described in {@link Core/data/Store#function-applyChangeset}
       * @param {Function} [transformFn] Optional function used to preprocess a changeset per store in a different
       * format, should return an object with the format expected by {@link Core/data/Store#function-applyChangeset}
       * @param {String} [phantomIdField] Field used by the backend when communicating a record being assigned a
       * proper id instead of a phantom id
       */
      applyChangeset(
        changes,
        transformFn = null,
        phantomIdField,
        logChanges = false,
      ) {
        const me = this,
          log = logChanges ? /* @__PURE__ */ new Map() : void 0;
        me.suspendAutoSync();
        me.suspendChangeTracking();
        for (const {
          store,
          phantomIdField: phantomIdField2,
        } of me.orderedCrudStores) {
          if (changes[store.id]) {
            const storeLog = store.applyChangeset(
              changes[store.id],
              transformFn,
              phantomIdField2 || me.phantomIdField,
              // mark this changeset as remote to enforce it
              true,
              logChanges,
            );
            if (storeLog) {
              log.set(store.id, storeLog);
            }
          }
        }
        me.resumeChangeTracking(true);
        me.resumeAutoSync(false);
        return log;
      }
      //endregion
      /**
       * Generates unique request identifier.
       * @internal
       * @template
       * @returns {Number} The request identifier.
       * @category CRUD
       */
      get requestId() {
        return Number.parseInt(`${Date.now()}${this._requestId++}`);
      }
      /**
       * Persists changes made on the registered stores to the server and/or receives changes made on the backend.
       * Usage:
       *
       * ```javascript
       * // persist and run a callback on request completion
       * crud.sync().then(
       *     () => console.log("Changes saved..."),
       *     ({ response, cancelled }) => console.log(`Error: ${cancelled ? 'Cancelled' : response.message}`)
       * );
       * ```
       *
       * ** Note: ** If there is an incomplete sync request in progress then system will queue the call and delay it
       * until previous request completion.
       * In this case {@link #event-syncDelayed} event will be fired.
       *
       * ** Note: ** Please take a look at {@link #config-autoSync} config. This option allows to persist changes
       * automatically after any data modification.
       *
       * ** Note: ** By default a sync request is only sent if there are any local {@link #property-changes}. To
       * always send a request when calling this function, configure {@link #config-forceSync} as `true`.
       *
       * @returns {Promise} Promise, which is resolved if request was successful.
       * Both the resolve and reject functions are passed a `state` object. State object has the following structure:
       * ```
       * {
       *     cancelled       : Boolean, // **optional** flag, which is present when promise was rejected
       *     rawResponse     : String,  // raw response from ajax request, either response xml or text
       *     rawResponseText : String,  // raw response text as String from ajax request
       *     response        : Object,  // processed response in form of object
       * }
       * ```
       * If promise was rejected by the {@link #event-beforeSync} event, `state` object will have this structure:
       * ```
       * {
       *     cancelled : true
       * }
       * ```
       * @category CRUD
       * @async
       */
      sync() {
        const me = this;
        me.clearTimeout("autoSync");
        if (me.activeRequests.sync) {
          me.trigger("syncDelayed");
          return (me.activeSyncPromise = me.activeSyncPromise.finally(() =>
            me.sync(),
          ));
        }
        return (me.activeSyncPromise = new Promise((resolve, reject) => {
          const pack = me.getChangesetPackage();
          if (!pack) {
            resolve(null);
            return;
          }
          if (me.trigger("beforeSync", { pack }) !== false) {
            me.trigger("syncStart", { pack });
            me.activeRequests.sync = {
              type: "sync",
              pack,
              resolve,
              reject,
              id: pack.requestId,
              desc: me.sendRequest({
                id: pack.requestId,
                data: me.encode(pack),
                type: "sync",
                success: me.onCrudRequestSuccess,
                failure: me.onCrudRequestFailure,
                thisObj: me,
              }),
            };
          } else {
            me.trigger("syncCanceled", { pack });
            reject({ cancelled: true });
          }
        }).catch((error) => {
          if (error && !error.cancelled) {
            throw error;
          }
          return error;
        }));
      }
      async onCrudRequestSuccess(rawResponse, fetchOptions, request) {
        const me = this,
          { type: requestType, id: requestId } = request;
        if (me.isDestroyed) return;
        let responseText = "";
        request = me.activeRequests[requestType];
        try {
          responseText = await rawResponse.text();
        } catch (e) {}
        if (me.isDestroyed) return;
        if ((request == null ? void 0 : request.id) !== requestId) {
          throw new Error(`Interleaved ${requestType} operation detected`);
        }
        me.activeRequests[requestType] = null;
        const response = await me.internalOnResponse(
          request,
          responseText,
          fetchOptions,
        );
        if (me.isDestroyed) return;
        if (
          !response ||
          (me.skipSuccessProperty
            ? (response == null ? void 0 : response.success) === false
            : !(response == null ? void 0 : response.success))
        ) {
          const error = {
            rawResponse,
            response,
            request,
          };
          if (response == null ? void 0 : response.message) {
            error.message = response.message;
          }
          request.reject(new CrudManagerRequestError(error));
        }
        me["crud" + StringHelper.capitalize(request.type) + "ed"] = true;
        request.resolve({ response, rawResponse, responseText, request });
      }
      async onCrudRequestFailure(rawResponse, fetchOptions, request) {
        var _a5;
        const me = this;
        if (me.isDestroyed) return;
        request = me.activeRequests[request.type];
        const signal =
            (_a5 =
              fetchOptions == null ? void 0 : fetchOptions.abortController) ==
            null
              ? void 0
              : _a5.signal,
          wasAborted = Boolean(signal == null ? void 0 : signal.aborted);
        if (!wasAborted) {
          let response,
            responseText = "";
          try {
            responseText = await rawResponse.text();
            response = me.decode(responseText);
          } catch (e) {}
          if (me.isDestroyed) return;
          me.triggerFailedRequestEvents(
            request,
            response,
            responseText,
            fetchOptions,
          );
          if (me.isDestroyed) return;
          request.reject(
            new CrudManagerRequestError({
              rawResponse,
              request,
            }),
          );
        }
        me.activeRequests[request.type] = null;
      }
      /**
       * Accepts all changes in all stores, resets the modification tracking:
       * * Clears change tracking for all records
       * * Clears added
       * * Clears modified
       * * Clears removed
       * Leaves the store in an "unmodified" state.
       * @category CRUD
       */
      acceptChanges() {
        this.crudStores.forEach((store) => store.store.acceptChanges());
      }
      /**
       * Reverts all changes in all stores and re-inserts any records that were removed locally. Any new uncommitted
       * records will be removed.
       * @category CRUD
       */
      revertChanges() {
        this.revertCrudStoreChanges();
      }
      revertCrudStoreChanges() {
        const { usesSingleAssignment } = this.eventStore;
        this.orderedCrudStores.forEach(
          ({ store }) =>
            (!store.isAssignmentStore || !usesSingleAssignment) &&
            store.revertChanges(),
        );
      }
      /**
       * Removes all stores and cancels active requests.
       * @category CRUD
       * @internal
       */
      doDestroy() {
        const me = this,
          { load, sync } = me.activeRequests;
        load && me.cancelRequest(load.desc, load.reject);
        sync && me.cancelRequest(sync.desc, sync.reject);
        while (me.crudStores.length > 0) {
          me.removeCrudStore(me.crudStores[0]);
        }
        super.doDestroy && super.doDestroy();
      }
    }),
    __publicField(_a4, "configurable", {
      /**
       * Convenience shortcut to set only the url to load from, when you do not need to supply any other config
       * options in the `load` section of the `transport` config.
       *
       * Using `loadUrl`:
       * ```javascript
       * {
       *     loadUrl : 'read.php
       * }
       * ```
       *
       * Equals the following `transport` config:
       * ```javascript
       * {
       *     transport : {
       *         load : {
       *             url : 'read.php'
       *         }
       *     }
       * }
       * ```
       *
       * When read at runtime, it will return the value from `transport.load.url`.
       *
       * @prp {String}
       */
      loadUrl: null,
      /**
       * Convenience shortcut to set only the url to sync to, when you do not need to supply any other config
       * options in the `sync` section of the `transport` config.
       *
       * Using `loadUrl`:
       * ```javascript
       * {
       *     syncUrl : 'sync.php
       * }
       * ```
       *
       * Equals the following `transport` config:
       * ```javascript
       * {
       *     transport : {
       *         load : {
       *             url : 'sync.php'
       *         }
       *     }
       * }
       * ```
       *
       * When read at runtime, it will return the value from `transport.sync.url`.
       *
       * @prp {String}
       */
      syncUrl: null,
      /**
       * Specify as `true` to force sync requests to be sent when calling `sync()`, even if there are no local
       * changes. Useful in a polling scenario, to keep client up to date with the backend.
       * @prp {Boolean}
       */
      forceSync: null,
    }),
    __publicField(_a4, "delayable", {
      // Postponed to next frame, to allow Scheduler created after CrudManager to inject its stores
      // (timeRanges, resourceTimeRanges)
      doAutoLoad: "raf",
    }),
    _a4
  );
};

// ../Scheduler/lib/Scheduler/crud/transport/AjaxTransport.js
var AjaxTransport_default = (Target) =>
  class AjaxTransport extends (Target || Base) {
    static get $name() {
      return "AjaxTransport";
    }
    /**
     * Configuration of the AJAX requests used by _Crud Manager_ to communicate with a server-side.
     *
     * ```javascript
     * transport : {
     *     load : {
     *         url       : 'http://mycool-server.com/load.php',
     *         // HTTP request parameter used to pass serialized "load"-requests
     *         paramName : 'data',
     *         // pass extra HTTP request parameter
     *         params    : {
     *             foo : 'bar'
     *         }
     *     },
     *     sync : {
     *         url     : 'http://mycool-server.com/sync.php',
     *         // specify Content-Type for requests
     *         headers : {
     *             'Content-Type' : 'application/json'
     *         }
     *     }
     * }
     *```
     * Since the class uses Fetch API you can use
     * any its [Request interface](https://developer.mozilla.org/en-US/docs/Web/API/Request) options:
     *
     * ```javascript
     * transport : {
     *     load : {
     *         url         : 'http://mycool-server.com/load.php',
     *         // HTTP request parameter used to pass serialized "load"-requests
     *         paramName   : 'data',
     *         // pass few Fetch API options
     *         method      : 'GET',
     *         credentials : 'include',
     *         cache       : 'no-cache'
     *     },
     *     sync : {
     *         url         : 'http://mycool-server.com/sync.php',
     *         // specify Content-Type for requests
     *         headers     : {
     *             'Content-Type' : 'application/json'
     *         },
     *         credentials : 'include'
     *     }
     * }
     *```
     *
     * An object where you can set the following possible properties:
     * @config {Object} transport
     * @property {Object} [transport.load] Load requests configuration:
     * @property {String} [transport.load.url] URL to request for data loading.
     * @property {String} [transport.load.method='GET'] HTTP method to be used for load requests.
     * @property {String} [transport.load.paramName='data'] Name of the parameter that will contain a serialized `load`
     * request. The value is mandatory for requests using `GET` method (default for `load`) so if the value is not
     * provided `data` string is used as default.
     * This value is optional for HTTP methods like `POST` and `PUT`, the request body will be used for data
     * transferring in these cases.
     * @property {Object} [transport.load.params] An object containing extra HTTP parameters to pass to the server when
     * sending a `load` request.
     *
     * ```javascript
     * transport : {
     *     load : {
     *         url       : 'http://mycool-server.com/load.php',
     *         // HTTP request parameter used to pass serialized "load"-requests
     *         paramName : 'data',
     *         // pass extra HTTP request parameter
     *         // so resulting URL will look like: http://mycool-server.com/load.php?userId=123456&data=...
     *         params    : {
     *             userId : '123456'
     *         }
     *     },
     *     ...
     * }
     * ```
     * @property {Object<String,String>} [transport.load.headers] An object containing headers to pass to each server request.
     *
     * ```javascript
     * transport : {
     *     load : {
     *         url       : 'http://mycool-server.com/load.php',
     *         // HTTP request parameter used to pass serialized "load"-requests
     *         paramName : 'data',
     *         // specify Content-Type for "load" requests
     *         headers   : {
     *             'Content-Type' : 'application/json'
     *         }
     *     },
     *     ...
     * }
     * ```
     * @property {Object} [transport.load.fetchOptions] **DEPRECATED:** Any Fetch API options can be simply defined on
     * the upper configuration level:
     * ```javascript
     * transport : {
     *     load : {
     *         url          : 'http://mycool-server.com/load.php',
     *         // HTTP request parameter used to pass serialized "load"-requests
     *         paramName    : 'data',
     *         // Fetch API options
     *         method       : 'GET',
     *         credentials  : 'include'
     *     },
     *     ...
     * }
     * ```
     * @property {Object} [transport.load.requestConfig] **DEPRECATED:** The config options can be defined on the upper
     * configuration level.
     * @property {Object} [transport.sync] Sync requests (`sync` in further text) configuration:
     * @property {String} [transport.sync.url] URL to request for `sync`.
     * @property {String} [transport.sync.method='POST'] HTTP request method to be used for `sync`.
     * @property {String} [transport.sync.paramName=undefined] Name of the parameter in which `sync` data will be
     * transferred. This value is optional for requests using methods like `POST` and `PUT`, the request body will be
     * used for data transferring in this case (default for `sync`). And the value is mandatory for requests using `GET`
     * method (if the value is not provided `data` string will be used as fallback).
     * @property {Object} [transport.sync.params] HTTP parameters to pass with an HTTP request handling `sync`.
     *
     * ```javascript
     * transport : {
     *     sync : {
     *         url    : 'http://mycool-server.com/sync.php',
     *         // extra HTTP request parameter
     *         params : {
     *             userId : '123456'
     *         }
     *     },
     *     ...
     * }
     * ```
     * @property {Object<String,String>} [transport.sync.headers] HTTP headers to pass with an HTTP request handling `sync`.
     *
     * ```javascript
     * transport : {
     *     sync : {
     *         url     : 'http://mycool-server.com/sync.php',
     *         // specify Content-Type for "sync" requests
     *         headers : {
     *             'Content-Type' : 'application/json'
     *         }
     *     },
     *     ...
     * }
     * ```
     * @property {Object} [transport.sync.fetchOptions] **DEPRECATED:** Any Fetch API options can be simply defined on
     * the upper configuration level:
     * ```javascript
     * transport : {
     *     sync : {
     *         url         : 'http://mycool-server.com/sync.php',
     *         credentials : 'include'
     *     },
     *     ...
     * }
     * ```
     * @property {Object} [transport.sync.requestConfig] **DEPRECATED:** The config options can be defined on the upper
     * configuration level.
     * @category CRUD
     */
    static get defaultMethod() {
      return {
        load: "GET",
        sync: "POST",
      };
    }
    /**
     * Cancels a sent request.
     * @param {Promise} requestPromise The Promise object wrapping the Request to be cancelled.
     * The _requestPromise_ is the value returned from the corresponding {@link #function-sendRequest} call.
     * @category CRUD
     */
    cancelRequest(requestPromise, reject) {
      var _a4;
      (_a4 = requestPromise.abort) == null ? void 0 : _a4.call(requestPromise);
      if (!this.isDestroying) {
        reject({ cancelled: true });
      }
    }
    shouldUseBodyForRequestData(packCfg, method, paramName) {
      return !(method === "HEAD" || method === "GET") && !paramName;
    }
    /**
     * Sends a _Crud Manager_ request to the server.
     * @param {Object} request The request configuration object having following properties:
     * @param {'load'|'sync'} request.type The request type. Either `load` or `sync`.
     * @param {String} request.url The URL for the request. Overrides the URL defined in the `transport` object
     * @param {String} request.data The encoded _Crud Manager_ request data.
     * @param {Object} request.params An object specifying extra HTTP params to send with the request.
     * @param {Function} request.success A function to be started on successful request transferring.
     * @param {String} request.success.rawResponse `Response` object returned by the [fetch api](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API).
     * @param {Function} request.failure A function to be started on request transfer failure.
     * @param {String} request.failure.rawResponse `Response` object returned by the [fetch api](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API).
     * @param {Object} request.thisObj `this` reference for the above `success` and `failure` functions.
     * @returns {Promise} The fetch Promise object.
     * @fires beforeSend
     * @async
     * @category CRUD
     */
    sendRequest(request) {
      const me = this,
        { data } = request,
        transportConfig = me.transport[request.type] || {},
        requestConfig = Objects.assign(
          {},
          transportConfig,
          transportConfig.requestConfig,
        );
      if (request.url) {
        requestConfig.url = request.url;
      }
      requestConfig.method =
        requestConfig.method || AjaxTransport.defaultMethod[request.type];
      requestConfig.params = Objects.assign(
        requestConfig.params || {},
        request.params,
      );
      let { paramName } = requestConfig;
      if (
        me.shouldUseBodyForRequestData(
          transportConfig,
          requestConfig.method,
          paramName,
        )
      ) {
        requestConfig.body = data;
        requestConfig.headers = requestConfig.headers || {};
        requestConfig.headers["Content-Type"] =
          requestConfig.headers["Content-Type"] || "application/json";
      } else {
        paramName = paramName || "data";
        requestConfig.params[paramName] = data;
      }
      if (!requestConfig.url) {
        throw new Error("Trying to request without URL specified");
      }
      delete requestConfig.requestConfig;
      delete requestConfig.paramName;
      let ajaxPromise, resultPromise;
      function performSend() {
        requestConfig.queryParams = requestConfig.params;
        delete requestConfig.params;
        let cancelled = false;
        const fetchOptions = Objects.assign(
          {},
          requestConfig,
          requestConfig.fetchOptions,
        );
        ajaxPromise = AjaxHelper.fetch(requestConfig.url, fetchOptions);
        return ajaxPromise
          .catch((error) => {
            var _a4, _b;
            ajaxPromise.done = true;
            (_a4 = me.trigger) == null
              ? void 0
              : _a4.call(me, "responseReceived", { success: false });
            const signal =
              (_b = fetchOptions.abortController) == null ? void 0 : _b.signal;
            if (signal) {
              cancelled = signal.aborted;
              if (!cancelled) {
                console.warn(error);
              }
            }
            return { error, cancelled };
          })
          .then((response) => {
            var _a4;
            ajaxPromise.done = true;
            (_a4 = me.trigger) == null
              ? void 0
              : _a4.call(me, "responseReceived", {
                  success: Boolean(response == null ? void 0 : response.ok),
                });
            const callback = (response == null ? void 0 : response.ok)
              ? request.success
              : request.failure;
            return callback == null
              ? void 0
              : callback.call(
                  request.thisObj || me,
                  response,
                  fetchOptions,
                  request,
                );
          });
      }
      const beforeSendResult = me.trigger("beforeSend", {
        params: requestConfig.params,
        requestType: request.type,
        requestConfig,
        config: request,
      });
      if (Objects.isPromise(beforeSendResult)) {
        resultPromise = beforeSendResult.then(performSend);
      } else {
        resultPromise = performSend();
      }
      resultPromise.abort = () => {
        var _a4;
        if (!ajaxPromise.done) {
          (_a4 = ajaxPromise.abort) == null ? void 0 : _a4.call(ajaxPromise);
        }
      };
      return resultPromise;
    }
  };

// ../Scheduler/lib/Scheduler/crud/encoder/JsonEncoder.js
var JsonEncoder_default = (Target) =>
  class JsonEncoder extends (Target || Base) {
    static get $name() {
      return "JsonEncoder";
    }
    static get defaultConfig() {
      return {
        /**
         * Configuration of the JSON encoder used by the _Crud Manager_.
         *
         * @config {Object}
         * @property {Object} encoder.requestData Static data to send with the data request.
         *
         * ```js
         * new CrudManager({
         *     // add static "foo" property to all requests data
         *     encoder : {
         *         requestData : {
         *             foo : 'Bar'
         *         }
         *     },
         *     ...
         * });
         * ```
         *
         * The above snippet will result adding "foo" property to all requests data:
         *
         * ```json
         *     {
         *         "requestId"   : 756,
         *         "type"        : "load",
         *
         *         "foo"         : "Bar",
         *
         *         "stores"      : [
         *             ...
         * ```
         * @category CRUD
         */
        encoder: {},
      };
    }
    /**
     * Encodes a request object to _JSON_ encoded string. If encoding fails (due to circular structure), it returns null.
     * Supposed to be overridden in case data provided by the _Crud Manager_ has to be transformed into format requested by server.
     * @param {Object} requestData The request to encode.
     * @returns {String} The encoded request.
     * @category CRUD
     */
    encode(requestData) {
      var _a4;
      requestData = Object.assign(
        {},
        (_a4 = this.encoder) == null ? void 0 : _a4.requestData,
        requestData,
      );
      return StringHelper.safeJsonStringify(requestData);
    }
    /**
     * Decodes (parses) a _JSON_ response string to an object. If parsing fails, it returns null.
     * Supposed to be overridden in case data provided by server has to be transformed into format requested by the _Crud Manager_.
     * @param {String} responseText The response text to decode.
     * @returns {Object} The decoded response.
     * @category CRUD
     */
    decode(responseText) {
      return StringHelper.safeJsonParse(responseText);
    }
  };

// ../Scheduler/lib/Scheduler/data/mixin/ProjectCrudManager.js
var ProjectCrudManager_default = (Target) =>
  class ProjectCrudManager extends (Target || Base).mixin(
    AbstractCrudManagerMixin_default,
    AjaxTransport_default,
    JsonEncoder_default,
  ) {
    //region Config
    static get defaultConfig() {
      return {
        project: null,
      };
    }
    startConfigure(config) {
      this.getConfig("project");
      super.startConfigure(config);
      this._changesToClear = /* @__PURE__ */ new Map();
    }
    async doAutoLoad() {
      const { project } = this;
      if (project) {
        await project.commitAsync();
      }
      return super.doAutoLoad();
    }
    applyProjectResponse(response) {
      const me = this,
        { project } = me;
      me.applyingProjectResponse = true;
      const startDateField = project.fieldMap.startDate,
        endDateField = project.fieldMap.endDate,
        startDate = ObjectHelper.getPath(response, startDateField.dataSource),
        endDate = ObjectHelper.getPath(response, endDateField.dataSource);
      if (typeof startDate === "string") {
        ObjectHelper.setPath(
          response,
          startDateField.dataSource,
          startDateField.convert(startDate),
        );
      }
      if (typeof endDate === "string") {
        ObjectHelper.setPath(
          response,
          endDateField.dataSource,
          endDateField.convert(endDate),
        );
      }
      project.setByDataSource(response);
      me._changesToClear.set(me, response);
      me.applyingProjectResponse = false;
    }
    loadCrudManagerData(response, options = {}) {
      const me = this,
        { project } = me;
      me.suspendChangeTracking();
      super.loadCrudManagerData(...arguments);
      if (response == null ? void 0 : response.project) {
        if (project.delayEnteringReplica && project.hasDataInStores) {
          project.ion({
            recordsUnlinked: () => {
              me.suspendChangeTracking();
              me.applyProjectResponse(response.project);
              me.resumeChangeTracking();
            },
            once: true,
          });
        } else {
          me.applyProjectResponse(response.project);
        }
      }
      me.resumeChangeTracking();
    }
    async sync() {
      const { project } = this;
      this.suspendAutoSync();
      if (project) {
        await project.commitAsync();
      }
      if (this.isDestroying) {
        return;
      }
      this.resumeAutoSync(false);
      return super.sync();
    }
    async applyResponse(request, response, options) {
      var _a4, _b, _c, _d, _e, _f;
      const me = this;
      if (
        me.isDestroyed ||
        ((_a4 = me.project) == null ? void 0 : _a4.isDestroyed)
      ) {
        return;
      }
      me.trigger("beforeApplyResponse");
      await super.applyResponse(request, response, options);
      if (
        (response == null ? void 0 : response.project) ||
        (me.supportShortSyncResponse &&
          ((_b = request == null ? void 0 : request.pack) == null
            ? void 0
            : _b.project))
      ) {
        me.applyProjectResponse(
          response.project ||
            ((_c = request == null ? void 0 : request.pack) == null
              ? void 0
              : _c.project),
        );
      }
      if (me.project) {
        let requestType = request.type;
        if (me.trackResponseType) {
          requestType = response.type || requestType;
        }
        const propagationFlag = `propagating${StringHelper.capitalize(requestType)}Changes`;
        me.suspendAutoSync();
        me[propagationFlag] = true;
        const loud =
          me.project.isInitialCommit && !me.project.silenceInitialCommit;
        await me.project.commitAsync();
        me[propagationFlag] = false;
        (_d = me.resumeAutoSync) == null ? void 0 : _d.call(me, loud);
        (_e = me.commitRespondedChanges) == null ? void 0 : _e.call(me);
      }
      (_f = me.trigger) == null ? void 0 : _f.call(me, "applyResponse");
    }
    applySyncResponse(...args) {
      var _a4;
      const me = this,
        stmDisabled = (_a4 = me.project) == null ? void 0 : _a4.stm.disabled;
      if (stmDisabled === false && me.ignoreRemoteChangesInSTM) {
        me.project.stm.disable();
      }
      me.suspendAutoSync();
      super.applySyncResponse(...args);
      me.resumeAutoSync(false);
      if (stmDisabled === false) {
        me.project.stm.enable();
      }
    }
    shouldClearRecordFieldChange(record, field2, value) {
      const oldValue = record.getValue(field2);
      field2 = record.getFieldDefinition(field2);
      return (field2 == null ? void 0 : field2.isEqual)
        ? field2.isEqual(oldValue, value)
        : ObjectHelper.isEqual(oldValue, value);
    }
    commitRespondedChanges() {
      this._changesToClear.forEach((changes, record) => {
        Object.entries(changes).forEach(([key, value]) => {
          if (this.shouldClearRecordFieldChange(record, key, value)) {
            delete record.meta.modified[key];
          }
        });
      });
      this._changesToClear.clear();
    }
    applyChangesToStore(storeDesc, storeResponse, storePack, ...rest) {
      const changesMap = super.applyChangesToStore(
        storeDesc,
        storeResponse,
        storePack,
        ...rest,
      );
      if (changesMap.size && this.project) {
        for (const [id, changes] of changesMap) {
          const record = storeDesc.store.getById(id);
          record && this._changesToClear.set(record, changes);
        }
      }
      return changesMap;
    }
  };

// ../Scheduler/lib/Scheduler/crud/AbstractCrudManager.js
var AbstractCrudManager = class extends Base.mixin(
  AbstractCrudManagerMixin_default,
) {
  //region Default config
  /**
   * The server revision stamp.
   * The _revision stamp_ is a number which should be incremented after each server-side change.
   * This property reflects the current version of the data retrieved from the server and gets updated after each
   * {@link Scheduler/crud/AbstractCrudManagerMixin#function-load} and {@link Scheduler/crud/AbstractCrudManagerMixin#function-sync} call.
   * @property {Number}
   * @readonly
   */
  get revision() {
    return this.crudRevision;
  }
  set revision(value) {
    this.crudRevision = value;
  }
  /**
   * Get or set data of {@link #property-crudStores} as a JSON string.
   *
   * Get a JSON string:
   * ```javascript
   *
   * const jsonString = scheduler.crudManager.json;
   *
   * // returned jsonString:
   * '{"eventsData":[...],"resourcesData":[...],...}'
   *
   * // object representation of the returned jsonString:
   * {
   *     resourcesData    : [...],
   *     eventsData       : [...],
   *     assignmentsData  : [...],
   *     dependenciesData : [...],
   *     timeRangesData   : [...],
   *     // data from other stores
   * }
   * ```
   *
   * Set a JSON string (to populate the CrudManager stores):
   *
   * ```javascript
   * scheduler.crudManager.json = '{"eventsData":[...],"resourcesData":[...],...}'
   * ```
   *
   * @property {String}
   */
  get json() {
    return StringHelper.safeJsonStringify(this);
  }
  set json(json) {
    if (typeof json === "string") {
      json = StringHelper.safeJsonParse(json);
    }
    this.forEachCrudStore((store) => {
      const dataName = `${store.storeId}Data`;
      if (json[dataName]) {
        store.data = json[dataName];
      }
    });
  }
  static get defaultConfig() {
    return {
      /**
       * Sets the list of stores controlled by the CRUD manager.
       *
       * When adding a store to the CrudManager, make sure the server response format is correct for `load` and `sync` requests.
       * Learn more in the [Working with data](#Scheduler/guides/data/crud_manager.md#loading-data) guide.
       *
       * Store can be provided as in instance, using its `storeId` or as an {@link #typedef-CrudManagerStoreDescriptor}
       * object.
       * @config {Core.data.Store[]|String[]|CrudManagerStoreDescriptor[]}
       */
      stores: null,
      /**
       * Encodes request to the server.
       * @function encode
       * @param {Object} request The request to encode.
       * @returns {String} The encoded request.
       * @abstract
       */
      /**
       * Decodes response from the server.
       * @function decode
       * @param {String} response The response to decode.
       * @returns {Object} The decoded response.
       * @abstract
       */
    };
  }
  //endregion
  //region Init
  construct(config = {}) {
    if (config.stores) {
      config.crudStores = config.stores;
      delete config.stores;
    }
    super.construct(config);
  }
  //endregion
  //region inline data
  /**
   * Returns the data from all CrudManager `crudStores` in a format that can be consumed by `inlineData`.
   *
   * Used by JSON.stringify to correctly convert this CrudManager to json.
   *
   * The returned data is identical to what {@link Scheduler/crud/AbstractCrudManager#property-inlineData} contains.
   *
   * ```javascript
   *
   * const json = scheduler.crudManager.toJSON();
   *
   * // json:
   * {
   *     eventsData : [...],
   *     resourcesData : [...],
   *     dependenciesData : [...],
   *     assignmentsData : [...],
   *     timeRangesData : [...],
   *     resourceTimeRangesData : [...],
   *     // ... other stores data
   * }
   * ```
   *
   * Output can be consumed by `inlineData`.
   *
   * ```javascript
   * const json = scheduler.crudManager.toJSON();
   *
   * // Plug it back in later
   * scheduler.crudManager.inlineData = json;
   * ```
   *
   * @function toJSON
   * @returns {Object}
   * @category JSON
   */
  toJSON() {
    const result = {};
    this.forEachCrudStore(
      (store, storeId) => (result[`${storeId}Data`] = store.toJSON()),
    );
    return result;
  }
  /**
   * Get or set data of CrudManager stores. The returned data is identical to what
   * {@link Scheduler/crud/AbstractCrudManager#function-toJSON} returns:
   *
   * ```javascript
   *
   * const data = scheduler.crudManager.inlineData;
   *
   * // data:
   * {
   *     eventsData : [...],
   *     resourcesData : [...],
   *     dependenciesData : [...],
   *     assignmentsData : [...],
   *     timeRangesData : [...],
   *     resourceTimeRangesData : [...],
   *     ... other stores data
   * }
   *
   *
   * // Plug it back in later
   * scheduler.crudManager.inlineData = data;
   * ```
   *
   * @property {Object}
   */
  get inlineData() {
    return this.toJSON();
  }
  set inlineData(data) {
    this.json = data;
  }
  //endregion
  //region Store collection (add, remove, get & iterate)
  set stores(stores2) {
    if (stores2 !== this.crudStores) {
      this.crudStores = stores2;
    }
  }
  /**
   * A list of registered stores whose server communication will be collected into a single batch.
   * Each store is represented by a _store descriptor_.
   * @member {CrudManagerStoreDescriptor[]} stores
   */
  get stores() {
    return this.crudStores;
  }
  //endregion
  /**
   * Returns true if the crud manager is currently loading data
   * @property {Boolean}
   * @readonly
   * @category CRUD
   */
  get isLoading() {
    return this.isCrudManagerLoading;
  }
  /**
   * Adds a store to the collection.
   *
   *```javascript
   * // append stores to the end of collection
   * crudManager.addStore([
   *     store1,
   *     // storeId
   *     'bar',
   *     // store descriptor
   *     {
   *         storeId : 'foo',
   *         store   : store3
   *     },
   *     {
   *         storeId         : 'bar',
   *         store           : store4,
   *         // to write all fields of modified records
   *         writeAllFields  : true
   *     }
   * ]);
   *```
   *
   * **Note:** Order in which stores are kept in the collection is very essential sometimes.
   * Exactly in this order the loaded data will be put into each store.
   *
   * When adding a store to the CrudManager, make sure the server response format is correct for `load` and `sync`
   * requests. Learn more in the [Working with data](#Scheduler/guides/data/crud_manager.md#loading-data) guide.
   *
   * @param {Core.data.Store|String|CrudManagerStoreDescriptor|Core.data.Store[]|String[]|CrudManagerStoreDescriptor[]} store
   * A store or list of stores. Each store might be specified by its instance, `storeId` or _descriptor_.
   * @param {Number} [position] The relative position of the store. If `fromStore` is specified the position will be
   * taken relative to it.
   * If not specified then store(s) will be appended to the end of collection.
   * Otherwise, it will be an index in stores collection.
   *
   * ```javascript
   * // insert stores store4, store5 to the start of collection
   * crudManager.addStore([ store4, store5 ], 0);
   * ```
   *
   * @param {String|Core.data.Store|CrudManagerStoreDescriptor} [fromStore] The store relative to which position
   * should be calculated. Can be defined as a store identifier, instance or descriptor (the result of
   * {@link Scheduler/crud/AbstractCrudManagerMixin#function-getStoreDescriptor} call).
   *
   * ```javascript
   * // insert store6 just before a store having storeId equal to 'foo'
   * crudManager.addStore(store6, 0, 'foo');
   *
   * // insert store7 just after store3 store
   * crudManager.addStore(store7, 1, store3);
   * ```
   */
  addStore(...args) {
    return this.addCrudStore(...args);
  }
  removeStore(...args) {
    return this.removeCrudStore(...args);
  }
  getStore(...args) {
    return this.getCrudStore(...args);
  }
  hasChanges(...args) {
    return this.crudStoreHasChanges(...args);
  }
  loadData(...args) {
    return this.loadCrudManagerData(...args);
  }
};
AbstractCrudManager._$name = "AbstractCrudManager";

// ../Scheduler/lib/Scheduler/model/mixin/ProjectModelCommon.js
var ProjectModelCommon_default = (Target) => {
  var _a4;
  return (
    (_a4 = class extends (Target || Model) {
      static get configurable() {
        return {
          // Documented in Gantt/Scheduler/SchedulerPro version of ./model/ProjectModel since types differ
          assignments: null,
          dependencies: null,
          resources: null,
          timeRanges: null,
        };
      }
      // Project is a Model which triggers events, therefore it can define event handlers using `onEvent` syntax. Event
      // handler can be a string (for another instance property), or a function. Therefore, it is impossible to tell them
      // apart and project model can not expose fields.
      // https://github.com/bryntum/support/issues/7457
      static get autoExposeFields() {
        return false;
      }
      //region Inline data
      get assignments() {
        return this.assignmentStore.allRecords;
      }
      updateAssignments(assignments) {
        this.assignmentStore.data = assignments;
      }
      get dependencies() {
        return this.dependencyStore.allRecords;
      }
      updateDependencies(dependencies) {
        this.dependencyStore.data = dependencies;
      }
      get resources() {
        return this.resourceStore.allRecords;
      }
      updateResources(resources) {
        this.resourceStore.data = resources;
      }
      get timeRanges() {
        return this.timeRangeStore.allRecords;
      }
      getTimeRanges(startDate, endDate) {
        const store = this.timeRangeStore,
          ret = [];
        for (const timeSpan of store) {
          if (timeSpan.isRecurring) {
            ret.push(
              ...timeSpan.getOccurrencesForDateRange(startDate, endDate),
            );
          } else if (
            timeSpan.startDate < endDate &&
            startDate < timeSpan.endDate
          ) {
            ret.push(timeSpan);
          }
        }
        return ret;
      }
      updateTimeRanges(timeRanges) {
        this.timeRangeStore.data = timeRanges;
      }
      getResourceTimeRanges(startDate, endDate) {
        const store = this.resourceTimeRangeStore,
          ret = [];
        for (const timeSpan of store) {
          if (timeSpan.isRecurring) {
            ret.push(
              ...timeSpan.getOccurrencesForDateRange(startDate, endDate),
            );
          } else if (
            timeSpan.startDate < endDate &&
            (!timeSpan.endDate || startDate < timeSpan.endDate)
          ) {
            ret.push(timeSpan);
          }
        }
        return ret;
      }
      //endregion
    }),
    __publicField(_a4, "$name", "ProjectModelCommon"),
    _a4
  );
};

// ../Scheduler/lib/Scheduler/model/ResourceTimeRangeModel.js
var ResourceTimeRangeModel = class extends TimeSpan.mixin(
  RecurringTimeSpan_default,
) {
  get domId() {
    return `${this.constructor.domIdPrefix}-${this.id}`;
  }
  //endregion
  // Used internally to differentiate between Event and ResourceTimeRange
  get isResourceTimeRange() {
    return true;
  }
  // To match EventModel API
  get resources() {
    return this.resource ? [this.resource] : [];
  }
  // To match EventModel API
  get $linkedResources() {
    return this.resources;
  }
};
__publicField(ResourceTimeRangeModel, "$name", "ResourceTimeRangeModel");
//region Fields
__publicField(ResourceTimeRangeModel, "fields", [
  /**
   * Id of the resource this time range is associated with
   * @field {String|Number} resourceId
   */
  "resourceId",
  /**
   * Controls this time range's primary color, defaults to using current themes default time range color.
   * @field {String} timeRangeColor
   */
  "timeRangeColor",
]);
__publicField(ResourceTimeRangeModel, "relations", {
  /**
   * The associated resource, retrieved using a relation to a ResourceStore determined by the value assigned
   * to `resourceId`. The relation also lets you access all time ranges on a resource through
   * {@link Scheduler.model.ResourceModel#property-timeRanges}`.
   * @member {Scheduler.model.ResourceModel} resource
   */
  resource: {
    foreignKey: "resourceId",
    foreignStore: "resourceStore",
    relatedCollectionName: "timeRanges",
    nullFieldOnRemove: true,
  },
});
__publicField(ResourceTimeRangeModel, "domIdPrefix", "resourcetimerange");
ResourceTimeRangeModel._$name = "ResourceTimeRangeModel";

// ../Scheduler/lib/Scheduler/data/ResourceTimeRangeStore.js
var ResourceTimeRangeStore = class extends AjaxStore.mixin(
  RecurringTimeSpansMixin_default,
) {
  static get defaultConfig() {
    return {
      /**
       * CrudManager must load stores in the correct order. Lowest first.
       * @private
       */
      loadPriority: 500,
      /**
       * CrudManager must sync stores in the correct order. Lowest first.
       * @private
       */
      syncPriority: 500,
      /**
       * This store should be linked to a ResourceStore to link the time ranges to resources
       * @config {Scheduler.data.ResourceStore}
       */
      resourceStore: null,
      modelClass: ResourceTimeRangeModel,
      storeId: "resourceTimeRanges",
    };
  }
  set resourceStore(store) {
    this._resourceStore = store;
    if (!this.isConfiguring) {
      this.initRelations(true);
    }
  }
  get resourceStore() {
    return this._resourceStore;
  }
  // Matching signature in EventStore to allow reusage of SchedulerStores#onInternalEventStoreChange()
  getResourcesForEvent(resourceTimeRange) {
    return [resourceTimeRange.resource];
  }
  /**
   * Get resource time ranges intersecting the specified date range for a resource.
   *
   * The result is sorted by `startDate`.
   *
   * @param {Object} options Options
   * @param {Scheduler.model.ResourceModel} options.resourceRecord Resource record
   * @param {Date} options.startDate Start date of the range
   * @param {Date} options.endDate End date of the range
   * @returns {Scheduler.model.ResourceTimeRangeModel[]}
   */
  getRanges({ resourceRecord, startDate, endDate }) {
    const rangesInDateRange = resourceRecord.timeRanges.flatMap((range) => {
      if (range.supportsRecurring) {
        return range.getOccurrencesForDateRange(startDate, endDate);
      }
      if (range.intersectsRange(startDate, endDate)) {
        return range;
      }
      return [];
    });
    return rangesInDateRange.sort(
      (span1, span2) => span1.startDate - span2.startDate,
    );
  }
};
__publicField(ResourceTimeRangeStore, "$name", "ResourceTimeRangeStore");
ResourceTimeRangeStore._$name = "ResourceTimeRangeStore";

// ../Scheduler/lib/Scheduler/data/plugin/StoreTimeZonePlugin.js
var StoreTimeZonePlugin = class extends InstancePlugin {
  get timeZone() {
    return this.client.project.timeZone;
  }
  // Overrides a Store's processRecord function to be able to convert records added by a dataset
  // before they are processed by the engine
  processRecord(record, isDataSet) {
    if (isDataSet || this.client.isLoadingData || record.timeZone !== void 0) {
      this.convertRecordToTimeZone(record);
    }
  }
  convertRecordToTimeZone(record, timeZone = this.timeZone) {
    var _a4, _b;
    if (record.timeZone !== timeZone) {
      record.$ignoreChange = true;
      if ((_a4 = record.baselines) == null ? void 0 : _a4.count) {
        for (const bl of record.baselines) {
          if (record.timeZone !== bl.timeZone) {
            bl.timeZone = record.timeZone;
          }
          bl.convertToTimeZone(timeZone);
        }
      }
      if ((_b = record.occurrences) == null ? void 0 : _b.length) {
        for (const o of record.occurrences) {
          if (record.timeZone !== o.timeZone) {
            o.timeZone = record.timeZone;
          }
          o.convertToTimeZone(timeZone);
        }
      }
      record.convertToTimeZone(timeZone);
      record.$ignoreChange = false;
    }
  }
  beforeSyncRecord({ record }) {
    if (record.timeZone != null) {
      record.$restoreTimeZone = record.timeZone;
      record.convertToTimeZone();
    }
  }
  afterSyncRecord({ record }) {
    if (record.$restoreTimeZone) {
      record.convertToTimeZone(record.$restoreTimeZone);
      record.$restoreTimeZone = null;
    }
  }
};
__publicField(StoreTimeZonePlugin, "$name", "storeTimeZonePlugin");
__publicField(StoreTimeZonePlugin, "pluginConfig", {
  before: ["processRecord"],
  assign: ["beforeSyncRecord", "afterSyncRecord"],
});
StoreTimeZonePlugin._$name = "StoreTimeZonePlugin";

// ../Scheduler/lib/Scheduler/model/mixin/ProjectModelTimeZoneMixin.js
var ProjectModelTimeZoneMixin_default = (Target) => {
  var _a4;
  return (
    (_a4 = class extends (Target || Model) {
      get _storesWithDates() {
        return [
          this.taskStore,
          this.timeRangeStore,
          this.resourceTimeRangeStore,
        ].filter((s) => s);
      }
      plugStore(store) {
        if (!store.hasPlugin(StoreTimeZonePlugin)) {
          store.addPlugins(StoreTimeZonePlugin);
        }
      }
      unplugStore(store) {
        var _a5;
        (_a5 = store.plugins.storeTimeZonePlugin) == null
          ? void 0
          : _a5.destroy();
      }
      attachStore(store) {
        super.attachStore(store);
        if (
          store &&
          this.timeZone != null &&
          this._storesWithDates.includes(store)
        ) {
          this.plugStore(store);
          this.convertStoresToTimeZone([store]);
        }
      }
      detachStore(store) {
        super.detachStore(store);
        if (store && !store.isDestroyed && this.timeZone != null) {
          this.convertStoresToTimeZone([store], null);
          this.unplugStore(store);
        }
      }
      relayStoreChange({ source, action, records, replaced }) {
        const me = this;
        if (me.timeZone != null && me._storesWithDates.includes(source)) {
          if (["add", "replace"].includes(action)) {
            if (
              !(records == null ? void 0 : records.length) &&
              (replaced == null ? void 0 : replaced.length)
            ) {
              records = replaced;
            }
            if (records.length) {
              records.forEach((record) => (record.timeZone = me.timeZone));
            }
          }
        }
      }
      convertStoresToTimeZone(stores2, timeZone = this.timeZone) {
        var _a5;
        const me = this,
          stmAutoRecord = (_a5 = me.stm) == null ? void 0 : _a5.autoRecord;
        if (stmAutoRecord) {
          me.stm.autoRecord = false;
        }
        for (const store of stores2) {
          store == null
            ? void 0
            : store.forEach((r) =>
                store.plugins.storeTimeZonePlugin.convertRecordToTimeZone(
                  r,
                  timeZone,
                ),
              );
        }
        if (stmAutoRecord) {
          me.stmAutoRecord = stmAutoRecord;
        }
      }
      updateTimeZone(timeZone, oldTimeZone) {
        const me = this,
          isConfiguring = me._isConfiguringTimeZone || me.isConfiguring;
        me.trigger("beforeTimeZoneChange", {
          timeZone,
          oldTimeZone,
          isConfiguring,
        });
        me.calendarManagerStore.forEach((calendar) => calendar.bumpVersion());
        me._storesWithDates.forEach((store) => me.plugStore(store));
        me.convertStoresToTimeZone(me._storesWithDates);
        if (me.startDate) {
          const startDate =
            oldTimeZone != null
              ? TimeZoneHelper.fromTimeZone(me.startDate, oldTimeZone)
              : me.startDate;
          me.startDate =
            timeZone != null
              ? TimeZoneHelper.toTimeZone(startDate, timeZone)
              : startDate;
        }
        me.ignoreRecordChanges = true;
        me.commitAsync().then(() => {
          if (!me.isDestroyed) {
            me.trigger("timeZoneChange", {
              timeZone,
              oldTimeZone,
              isConfiguring,
            });
          }
          delete me._isConfiguringTimeZone;
        });
      }
    }),
    __publicField(_a4, "$name", "ProjectModelTimeZoneMixin"),
    __publicField(_a4, "configurable", {
      /**
       * Set to a IANA time zone (i.e. `Europe/Stockholm`) or a UTC offset in minutes (i.e. `-120`). This will
       * convert all events, tasks and time ranges to the specified time zone or offset. It will also affect the
       * displayed timeline's headers as well at the start and end date of it.
       *
       * There is currently no built-in time zone support in JavaScript which means that the converted dates
       * technically still are in the local system time zone, but adjusted to match the configured time zone.
       *
       * ### DST
       * If a IANA time zone is provided, there will be support for DST. But if local system time zone has DST that
       * will affect the time zone conversion at the exact hour when the local system time zone switches DST on and
       * off.
       *
       * *For example:*
       * 1. The local system time zone is `Europe/Stockholm` (which is UTC+1 or UTC+2 when DST).
       * 2. The date `2022-03-27T07:00:00Z` (which is UTC) is converted to `America/Chicago` (which is UTC-6 or UTC-5
       *    when DST).
       * 3. The converted JS date will be created from `2022-03-27T02:00:00` which is exactly the hour when
       *    `Europe/Stockholm` adds an DST hour. This has the effect that the converted date shows up incorrectly as
       *    `2022-03-27T03:00` instead.
       *
       * If a UTC offset is provided, there is no DST support at all.
       *
       * ### Editing
       * If creating new records or editing existing record dates, the dates will be interpreted as in the selected
       * time zone.
       *
       * If you want to create new records with dates that either should be interpreted as local system time zone or
       * from any other time zone, specify the {@link Scheduler.model.mixin.TimeZonedDatesMixin#field-timeZone} field
       * on the record.
       *
       * ### Saving
       * When saving or syncing data, the dates will be restored to local system time and converted to JSON
       * ISO formatted.
       *
       * @prp {String|Number} [timeZone]
       * @category Advanced
       */
      timeZone: {
        // Don't ingest the config eagerly because it relies on project being present.
        // Lazy means it waits for ingestion until timeZone property is referenced.
        $config: "lazy",
        value: null,
      },
    }),
    _a4
  );
};

// ../Scheduler/lib/Scheduler/model/TimeRangeModel.js
var TimeRangeModel = class extends TimeSpan.mixin(RecurringTimeSpan_default) {
  /**
   * @hidefields children, parentId, parentIndex
   */
  afterConstruct() {
    if (!this.endDate) {
      this.endDate = this.startDate;
    }
    super.afterConstruct();
  }
};
__publicField(TimeRangeModel, "$name", "TimeRangeModel");
TimeRangeModel._$name = "TimeRangeModel";

// ../Scheduler/lib/Scheduler/data/TimeRangeStore.js
var TimeRangeStore = class extends AjaxStore.mixin(
  RecurringTimeSpansMixin_default,
) {};
__publicField(TimeRangeStore, "$name", "TimeRangeStore");
__publicField(TimeRangeStore, "defaultConfig", {
  /**
   * CrudManager must load stores in the correct order. Lowest first.
   * @private
   */
  loadPriority: 500,
  /**
   * CrudManager must sync stores in the correct order. Lowest first.
   * @private
   */
  syncPriority: 500,
  modelClass: TimeRangeModel,
  storeId: "timeRanges",
});
TimeRangeStore._$name = "TimeRangeStore";

// ../Scheduler/lib/Scheduler/model/mixin/ProjectModelMixin.js
var ProjectModelMixin_default = (Target) => {
  var _a4;
  return (
    (_a4 = class extends (
      (Target || Model).mixin(
        ProjectModelCommon_default,
        ProjectModelTimeZoneMixin_default,
      )
    ) {
      static get $name() {
        return "ProjectModelMixin";
      }
      //region Config
      static get defaultConfig() {
        return {
          /**
           * State tracking manager instance the project relies on
           * @member {Core.data.stm.StateTrackingManager} stm
           * @category Advanced
           */
          /**
           * Configuration options to provide to the STM manager
           *
           * @config {StateTrackingManagerConfig|Core.data.stm.StateTrackingManager}
           * @category Advanced
           */
          stm: {},
          timeRangeModelClass: TimeRangeModel,
          resourceTimeRangeModelClass: ResourceTimeRangeModel,
          /**
           * The constructor to create a time range store instance with. Should be a class subclassing the
           * {@link Scheduler.data.TimeRangeStore}
           * @config {Scheduler.data.TimeRangeStore|Object}
           * @typings {typeof TimeRangeStore|object}
           * @category Models & Stores
           */
          timeRangeStoreClass: TimeRangeStore,
          /**
           * The constructor to create a resource time range store instance with. Should be a class subclassing the
           * {@link Scheduler.data.ResourceTimeRangeStore}
           * @config {Scheduler.data.ResourceTimeRangeStore|Object}
           * @typings {typeof ResourceTimeRangeStore|object}
           * @category Models & Stores
           */
          resourceTimeRangeStoreClass: ResourceTimeRangeStore,
          /**
           * The initial data, to fill the {@link #property-timeRangeStore timeRangeStore} with.
           * Should be an array of {@link Scheduler.model.TimeSpan TimeSpan} or its configuration objects.
           *
           * @config {Scheduler.model.TimeSpan[]} [timeRangesData]
           * @category Legacy inline data
           */
          /**
           * The initial data, to fill the {@link #property-resourceTimeRangeStore resourceTimeRangeStore} with.
           * Should be an array of {@link Scheduler.model.ResourceTimeRangeModel ResourceTimeRangeModel} or it's
           * configuration objects.
           *
           * @config {Scheduler.model.ResourceTimeRangeModel[]} [resourceTimeRangesData]
           * @category Legacy inline data
           */
          eventStore: {},
          assignmentStore: {},
          dependencyStore: {},
          resourceStore: {},
          timeRangesData: null,
          resourceTimeRangesData: null,
        };
      }
      //endregion
      //region Properties
      /**
       * Get or set data of project stores. The returned data is identical to what
       * {@link #function-toJSON} returns:
       *
       * ```javascript
       *
       * const data = scheduler.project.inlineData;
       *
       * // data:
       * {
       *     eventsData             : [...],
       *     resourcesData          : [...],
       *     dependenciesData       : [...],
       *     assignmentsData        : [...],
       *     resourceTimeRangesData : [...],
       *     timeRangesData         : [...]
       * }
       *
       *
       * // Plug it back in later
       * scheduler.project.inlineData = data;
       * ```
       *
       * @property {Object}
       * @category Inline data
       */
      get inlineData() {
        return StringHelper.safeJsonParse(super.json);
      }
      set inlineData(inlineData) {
        this.json = inlineData;
      }
      //endregion
      //region Functions
      /**
       * Accepts a "data package" consisting of data for the projects stores, which is then loaded into the stores.
       *
       * The package can hold data for `EventStore`, `AssignmentStore`, `ResourceStore`, `DependencyStore`,
       * `TimeRangeStore` and `ResourceTimeRangeStore`. It uses the same format as when creating a project with inline
       * data:
       *
       * ```javascript
       * await project.loadInlineData({
       *     eventsData             : [...],
       *     resourcesData          : [...],
       *     assignmentsData        : [...],
       *     dependenciesData       : [...],
       *     resourceTimeRangesData : [...],
       *     timeRangesData         : [...]
       * });
       * ```
       *
       * After populating the stores it commits the project, starting its calculations. By awaiting `loadInlineData()` you
       * can be sure that project calculations are finished.
       *
       * @function loadInlineData
       * @param {Object} dataPackage A data package as described above
       * @fires load
       * @async
       * @category Inline data
       */
      /**
       * Project changes (CRUD operations to records in its stores) are automatically committed on a buffer to the
       * underlying graph based calculation engine. The engine performs it calculations async.
       *
       * By calling this function, the commit happens right away. And by awaiting it you are sure that project
       * calculations are finished and that references between records are up to date.
       *
       * The returned promise is resolved with an object. If that object has `rejectedWith` set, there has been a conflict and the calculation failed.
       *
       * ```javascript
       * // Move an event in time
       * eventStore.first.shift(1);
       *
       * // Trigger calculations directly and wait for them to finish
       * const result = await project.commitAsync();
       *
       * if (result.rejectedWith) {
       *     // there was a conflict during the scheduling
       * }
       * ```
       *
       * @async
       * @function commitAsync
       * @category Common
       */
      //endregion
      //region Init
      construct(config = {}) {
        super.construct(...arguments);
        if (config.timeRangesData) {
          this.timeRangeStore.data = config.timeRangesData;
        }
        if (config.resourceTimeRangesData) {
          this.resourceTimeRangeStore.data = config.resourceTimeRangesData;
        }
      }
      afterConstruct() {
        super.afterConstruct();
        const me = this;
        !me.timeRangeStore.stm && me.stm.addStore(me.timeRangeStore);
        !me.resourceTimeRangeStore.stm &&
          me.stm.addStore(me.resourceTimeRangeStore);
      }
      //endregion
      //region Attaching stores
      // Attach to a store, relaying its change events
      attachStore(store) {
        if (store) {
          store.ion({
            name: store.$$name,
            change: "relayStoreChange",
            thisObj: this,
          });
        }
        super.attachStore(store);
      }
      // Detach a store, stop relaying its change events
      detachStore(store) {
        if (store) {
          this.detachListeners(store.$$name);
          super.detachStore(store);
        }
      }
      relayStoreChange(event) {
        super.relayStoreChange(event);
        return this.trigger("change", {
          store: event.source,
          ...event,
          source: this,
        });
      }
      updateTimeRangeStore(store, oldStore) {
        this.detachStore(oldStore);
        this.attachStore(store);
        if (oldStore) {
          oldStore.project = null;
        }
        if (store) {
          store.project = this;
        }
      }
      setTimeRangeStore(store) {
        this.timeRangeStore = store;
      }
      changeTimeRangeStore(store) {
        if (store && !store.isStore) {
          store = this.timeRangeStoreClass.new(
            {
              modelClass: this.timeRangeModelClass,
            },
            store,
          );
        }
        return store;
      }
      updateResourceTimeRangeStore(store, oldStore) {
        this.detachStore(oldStore);
        this.attachStore(store);
        if (oldStore) {
          oldStore.project = null;
        }
        if (store) {
          store.project = this;
        }
      }
      changeResourceTimeRangeStore(store) {
        if (store && !store.isStore) {
          store = this.resourceTimeRangeStoreClass.new(
            {
              modelClass: this.resourceTimeRangeModelClass,
            },
            store,
          );
        }
        return store;
      }
      setResourceTimeRangeStore(store) {
        this.resourceTimeRangeStore = store;
      }
      //endregion
      //region Inline data
      get events() {
        return this.eventStore.allRecords;
      }
      updateEvents(events) {
        this.eventStore.data = events;
      }
      get resourceTimeRanges() {
        return this.resourceTimeRangeStore.allRecords;
      }
      updateResourceTimeRanges(resourceTimeRanges) {
        this.resourceTimeRangeStore.data = resourceTimeRanges;
      }
      async loadInlineData(data) {
        this.isLoadingInlineData = true;
        if (data.resourceTimeRangesData) {
          this.resourceTimeRangeStore.data = data.resourceTimeRangesData;
        }
        if (data.timeRangesData) {
          this.timeRangeStore.data = data.timeRangesData;
        }
        return super.loadInlineData(data);
      }
      //endregion
      //region JSON
      /**
       * Returns the data from the records of the projects stores, in a format that can be consumed by `loadInlineData()`.
       *
       * Used by JSON.stringify to correctly convert this record to json.
       *
       *
       * ```javascript
       * const project = new ProjectModel({
       *     eventsData             : [...],
       *     resourcesData          : [...],
       *     assignmentsData        : [...],
       *     dependenciesData       : [...],
       *     resourceTimeRangesData : [...],
       *     timeRangesData         : [...]
       * });
       *
       * const json = project.toJSON();
       *
       * // json:
       * {
       *     eventsData             : [...],
       *     resourcesData          : [...],
       *     dependenciesData       : [...],
       *     assignmentsData        : [...],
       *     resourceTimeRangesData : [...],
       *     timeRangesData         : [...]
       * }
       * ```
       *
       * Output can be consumed by `loadInlineData()`:
       *
       * ```javascript
       * const json = project.toJSON();
       *
       * // Plug it back in later
       * project.loadInlineData(json);
       * ```
       *
       * @returns {Object}
       * @category Inline data
       */
      toJSON() {
        const me = this,
          result = {
            eventsData: me.eventStore.toJSON(),
            resourcesData: me.resourceStore.toJSON(),
            dependenciesData: me.dependencyStore.toJSON(),
            timeRangesData: me.timeRangeStore.toJSON(),
            resourceTimeRangesData: me.resourceTimeRangeStore.toJSON(),
          };
        if (!me.eventStore.usesSingleAssignment) {
          result.assignmentsData = me.assignmentStore.toJSON();
        }
        return result;
      }
      /**
       * Get or set project data (records from its stores) as a JSON string.
       *
       * Get a JSON string:
       *
       * ```javascript
       * const project = new ProjectModel({
       *     eventsData             : [...],
       *     resourcesData          : [...],
       *     assignmentsData        : [...],
       *     dependenciesData       : [...],
       *     resourceTimeRangesData : [...],
       *     timeRangesData         : [...]
       * });
       *
       * const jsonString = project.json;
       *
       * // jsonString:
       * '{"eventsData":[...],"resourcesData":[...],...}'
       * ```
       *
       * Set a JSON string (to populate the project stores):
       *
       * ```javascript
       * project.json = '{"eventsData":[...],"resourcesData":[...],...}'
       * ```
       *
       * @property {String}
       * @category Inline data
       */
      get json() {
        return super.json;
      }
      changeJson(json) {
        if (typeof json === "string") {
          json = StringHelper.safeJsonParse(json);
        }
        return json;
      }
      updateJson(json) {
        json && this.loadInlineData(json);
      }
      //endregion
      afterChange(toSet, wasSet) {
        super.afterChange(...arguments);
        if (wasSet.calendar) {
          this.trigger("calendarChange");
        }
      }
      doDestroy() {
        this.timeRangeStore.destroy();
        this.resourceTimeRangeStore.destroy();
        super.doDestroy();
      }
    }),
    __publicField(_a4, "configurable", {
      /**
       * Project data as a JSON string, used to populate its stores.
       *
       * ```javascript
       * const project = new ProjectModel({
       *     json : '{"eventsData":[...],"resourcesData":[...],...}'
       * }
       * ```
       *
       * @config {String}
       * @category Inline data
       */
      json: null,
      /**
       * The {@link Core.data.Store store} holding the time ranges information.
       *
       * See also {@link Scheduler.model.TimeSpan}
       *
       * @member {Core.data.Store} timeRangeStore
       * @category Models & Stores
       */
      /**
       * A {@link Core.data.Store} instance or a config object.
       * @config {Core.data.Store|StoreConfig}
       * @category Models & Stores
       */
      timeRangeStore: {
        value: {},
        $config: "nullify",
      },
      /**
       * The {@link Scheduler.data.ResourceTimeRangeStore store} holding the resource time ranges information.
       *
       * See also {@link Scheduler.model.ResourceTimeRangeModel}
       *
       * @member {Scheduler.data.ResourceTimeRangeStore} resourceTimeRangeStore
       * @category Models & Stores
       */
      /**
       * A {@link Scheduler.data.ResourceTimeRangeStore} instance or a config object.
       * @config {Scheduler.data.ResourceTimeRangeStore|ResourceTimeRangeStoreConfig}
       * @category Models & Stores
       */
      resourceTimeRangeStore: {
        value: {},
        $config: "nullify",
      },
      // Documented in Scheduler/SchedulerPro versions of model/ProjectModel since types differ
      events: null,
      resourceTimeRanges: null,
    }),
    _a4
  );
};

// ../Scheduler/lib/Scheduler/model/mixin/ProjectCurrentConfig.js
var ProjectCurrentConfig_default = (Target) =>
  class ProjectCurrentConfig extends Target {
    // This function is not meant to be called by any code other than Base#getCurrentConfig().
    // It extracts the current configs/fields for the project, with special handling for inline data
    getCurrentConfig(options) {
      const me = this,
        result = super.getCurrentConfig(options);
      if (result) {
        for (const storeName of [
          "eventStore",
          "resourceStore",
          "assignmentStore",
          "dependencyStore",
          "timeRangeStore",
          "resourceTimeRangeStore",
        ]) {
          const store = me[storeName];
          if (store) {
            if (store.count) {
              result[store.id + "Data"] = store.getInlineData(options);
            }
            const storeState = store.getCurrentConfig(options);
            if (storeState && Object.keys(storeState).length > 0) {
              if (Object.keys(storeState).length === 1 && storeState.data) {
                delete result[storeName];
              } else {
                result[storeName] = Object.assign(
                  result[storeName] || {},
                  storeState,
                );
              }
            } else if (
              result[storeName] &&
              Object.keys(result[storeName]).length === 0
            ) {
              delete result[storeName];
            }
          }
        }
        if (me.taskStore.isTaskStore) {
          delete result.eventModelClass;
          delete result.eventStoreClass;
          delete result.children;
        }
        return result;
      }
    }
  };

// ../Scheduler/lib/Scheduler/data/util/ModelPersistencyManager.js
var ModelPersistencyManager = class extends Base {
  // region Event attachers
  set eventStore(newEventStore) {
    const me = this;
    me.eventStoreDetacher && me.eventStoreDetacher();
    me._eventStore = newEventStore;
    if (newEventStore && newEventStore.autoCommit) {
      me.eventStoreDetacher = newEventStore.ion({
        beforecommit: me.onEventStoreBeforeSync,
        thisObj: me,
        detachable: true,
        // Just in case
        prio: 100,
      });
    }
  }
  get eventStore() {
    return this._eventStore;
  }
  set resourceStore(newResourceStore) {
    const me = this;
    me.resourceStoreDetacher && me.resourceStoreDetacher();
    me._resourceStore = newResourceStore;
    if (newResourceStore && newResourceStore.autoCommit) {
      me.resourceStoreDetacher = newResourceStore.ion({
        beforecommit: me.onResourceStoreBeforeSync,
        thisObj: me,
        detachable: true,
        // Just in case
        prio: 100,
      });
    }
  }
  get resourceStore() {
    return this._resourceStore;
  }
  set assignmentStore(newAssignmentStore) {
    const me = this;
    me.assignmentStoreDetacher && me.assignmentStoreDetacher();
    me._assignmentStore = newAssignmentStore;
    if (newAssignmentStore && newAssignmentStore.autoSync) {
      me.assignmentStoreDetacher = newAssignmentStore.ion({
        beforecommit: me.onAssignmentStoreBeforeSync,
        thisObj: me,
        detachable: true,
        // Just in case
        prio: 100,
      });
    }
  }
  get assignmentStore() {
    return this._assignmentStore;
  }
  set dependencyStore(newDependencyStore) {
    const me = this;
    me.dependencyStoreDetacher && me.dependencyStoreDetacher();
    me._dependencyStore = newDependencyStore;
    if (newDependencyStore && newDependencyStore.autoSync) {
      me.dependencyStoreDetacher = newDependencyStore.ion({
        beforecommit: me.onDependencyStoreBeforeSync,
        thisObj: me,
        detachable: true,
        // Just in case
        prio: 100,
      });
    }
  }
  get dependencyStore() {
    return this._dependencyStore;
  }
  // endregion
  // region Event handlers
  onEventStoreBeforeSync({ changes }) {
    const me = this;
    me.removeNonPersistableRecordsToCreate(changes);
    return me.shallContinueSync(changes);
  }
  onResourceStoreBeforeSync({ changes }) {
    const me = this;
    me.removeNonPersistableRecordsToCreate(changes);
    return me.shallContinueSync(changes);
  }
  onAssignmentStoreBeforeSync({ changes }) {
    const me = this;
    me.removeNonPersistableRecordsToCreate(changes);
    return me.shallContinueSync(changes);
  }
  onDependencyStoreBeforeSync({ changes }) {
    const me = this;
    me.removeNonPersistableRecordsToCreate(changes);
    return me.shallContinueSync(changes);
  }
  // endregion
  // region Management rules
  removeNonPersistableRecordsToCreate(changes) {
    const recordsToCreate = changes.added || [];
    let r, i;
    for (i = recordsToCreate.length - 1; i >= 0; --i) {
      r = recordsToCreate[i];
      if (!r.isPersistable) {
        recordsToCreate.splice(recordsToCreate.indexOf(r), 1);
      }
    }
    if (recordsToCreate.length === 0) {
      changes.added.length = 0;
    }
  }
  shallContinueSync(options) {
    return Boolean(
      (options.added && options.added.length > 0) ||
      (options.modified && options.modified.length > 0) ||
      (options.removed && options.removed.length > 0),
    );
  }
  // endregion
};
ModelPersistencyManager._$name = "ModelPersistencyManager";

// ../Engine/lib/Engine/vendor/later/later.js
var diffSecond = (date, diff) => {
  return new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
    date.getHours(),
    date.getMinutes(),
    date.getSeconds() + diff,
    date.getMilliseconds(),
  );
};
var later = (function () {
  "use strict";
  var later2 = {
    version: "1.2.0",
  };
  if (!Array.prototype.indexOf) {
    Array.prototype.indexOf = function (searchElement) {
      "use strict";
      if (this == null) {
        throw new TypeError();
      }
      var t = Object(this);
      var len = t.length >>> 0;
      if (len === 0) {
        return -1;
      }
      var n = 0;
      if (arguments.length > 1) {
        n = Number(arguments[1]);
        if (n != n) {
          n = 0;
        } else if (n != 0 && n != Infinity && n != -Infinity) {
          n = (n > 0 || -1) * Math.floor(Math.abs(n));
        }
      }
      if (n >= len) {
        return -1;
      }
      var k = n >= 0 ? n : Math.max(len - Math.abs(n), 0);
      for (; k < len; k++) {
        if (k in t && t[k] === searchElement) {
          return k;
        }
      }
      return -1;
    };
  }
  if (!String.prototype.trim) {
    String.prototype.trim = function () {
      return this.replace(/^\s+|\s+$/g, "");
    };
  }
  later2.array = {};
  later2.array.sort = function (arr, zeroIsLast) {
    arr.sort(function (a, b) {
      return +a - +b;
    });
    if (zeroIsLast && arr[0] === 0) {
      arr.push(arr.shift());
    }
  };
  later2.array.next = function (val, values, extent) {
    var cur,
      zeroIsLargest = extent[0] !== 0,
      nextIdx = 0;
    for (var i = values.length - 1; i > -1; --i) {
      cur = values[i];
      if (cur === val) {
        return cur;
      }
      if (cur > val || (cur === 0 && zeroIsLargest && extent[1] > val)) {
        nextIdx = i;
        continue;
      }
      break;
    }
    return values[nextIdx];
  };
  later2.array.nextInvalid = function (val, values, extent) {
    var min2 = extent[0],
      max = extent[1],
      len = values.length,
      zeroVal = values[len - 1] === 0 && min2 !== 0 ? max : 0,
      next = val,
      i = values.indexOf(val),
      start = next;
    while (next === (values[i] || zeroVal)) {
      next++;
      if (next > max) {
        next = min2;
      }
      i++;
      if (i === len) {
        i = 0;
      }
      if (next === start) {
        return void 0;
      }
    }
    return next;
  };
  later2.array.prev = function (val, values, extent) {
    var cur,
      len = values.length,
      zeroIsLargest = extent[0] !== 0,
      prevIdx = len - 1;
    for (var i = 0; i < len; i++) {
      cur = values[i];
      if (cur === val) {
        return cur;
      }
      if (cur < val || (cur === 0 && zeroIsLargest && extent[1] < val)) {
        prevIdx = i;
        continue;
      }
      break;
    }
    return values[prevIdx];
  };
  later2.array.prevInvalid = function (val, values, extent) {
    var min2 = extent[0],
      max = extent[1],
      len = values.length,
      zeroVal = values[len - 1] === 0 && min2 !== 0 ? max : 0,
      next = val,
      i = values.indexOf(val),
      start = next;
    while (next === (values[i] || zeroVal)) {
      next--;
      if (next < min2) {
        next = max;
      }
      i--;
      if (i === -1) {
        i = len - 1;
      }
      if (next === start) {
        return void 0;
      }
    }
    return next;
  };
  later2.day = later2.D = {
    name: "day",
    range: 86400,
    val: function (d) {
      return d.D || (d.D = later2.date.getDate.call(d));
    },
    isValid: function (d, val) {
      return later2.D.val(d) === (val || later2.D.extent(d)[1]);
    },
    extent: function (d) {
      if (d.DExtent) return d.DExtent;
      var month2 = later2.M.val(d),
        max = later2.DAYS_IN_MONTH[month2 - 1];
      if (month2 === 2 && later2.dy.extent(d)[1] === 366) {
        max = max + 1;
      }
      return (d.DExtent = [1, max]);
    },
    start: function (d) {
      return (
        d.DStart ||
        (d.DStart = later2.date.next(
          later2.Y.val(d),
          later2.M.val(d),
          later2.D.val(d),
        ))
      );
    },
    end: function (d) {
      return (
        d.DEnd ||
        (d.DEnd = later2.date.prev(
          later2.Y.val(d),
          later2.M.val(d),
          later2.D.val(d),
        ))
      );
    },
    next: function (d, val) {
      val = val > later2.D.extent(d)[1] ? 1 : val;
      var month2 = later2.date.nextRollover(d, val, later2.D, later2.M),
        DMax = later2.D.extent(month2)[1];
      val = val > DMax ? 1 : val || DMax;
      return later2.date.next(later2.Y.val(month2), later2.M.val(month2), val);
    },
    prev: function (d, val) {
      var month2 = later2.date.prevRollover(d, val, later2.D, later2.M),
        DMax = later2.D.extent(month2)[1];
      return later2.date.prev(
        later2.Y.val(month2),
        later2.M.val(month2),
        val > DMax ? DMax : val || DMax,
      );
    },
  };
  later2.dayOfWeekCount = later2.dc = {
    name: "day of week count",
    range: 604800,
    val: function (d) {
      return d.dc || (d.dc = Math.floor((later2.D.val(d) - 1) / 7) + 1);
    },
    isValid: function (d, val) {
      return (
        later2.dc.val(d) === val ||
        (val === 0 && later2.D.val(d) > later2.D.extent(d)[1] - 7)
      );
    },
    extent: function (d) {
      return (
        d.dcExtent || (d.dcExtent = [1, Math.ceil(later2.D.extent(d)[1] / 7)])
      );
    },
    start: function (d) {
      return (
        d.dcStart ||
        (d.dcStart = later2.date.next(
          later2.Y.val(d),
          later2.M.val(d),
          Math.max(1, (later2.dc.val(d) - 1) * 7 + 1 || 1),
        ))
      );
    },
    end: function (d) {
      return (
        d.dcEnd ||
        (d.dcEnd = later2.date.prev(
          later2.Y.val(d),
          later2.M.val(d),
          Math.min(later2.dc.val(d) * 7, later2.D.extent(d)[1]),
        ))
      );
    },
    next: function (d, val) {
      val = val > later2.dc.extent(d)[1] ? 1 : val;
      var month2 = later2.date.nextRollover(d, val, later2.dc, later2.M),
        dcMax = later2.dc.extent(month2)[1];
      val = val > dcMax ? 1 : val;
      var next = later2.date.next(
        later2.Y.val(month2),
        later2.M.val(month2),
        val === 0 ? later2.D.extent(month2)[1] - 6 : 1 + 7 * (val - 1),
      );
      if (next.getTime() <= d.getTime()) {
        month2 = later2.M.next(d, later2.M.val(d) + 1);
        return later2.date.next(
          later2.Y.val(month2),
          later2.M.val(month2),
          val === 0 ? later2.D.extent(month2)[1] - 6 : 1 + 7 * (val - 1),
        );
      }
      return next;
    },
    prev: function (d, val) {
      var month2 = later2.date.prevRollover(d, val, later2.dc, later2.M),
        dcMax = later2.dc.extent(month2)[1];
      val = val > dcMax ? dcMax : val || dcMax;
      return later2.dc.end(
        later2.date.prev(
          later2.Y.val(month2),
          later2.M.val(month2),
          1 + 7 * (val - 1),
        ),
      );
    },
  };
  later2.dayOfWeek =
    later2.dw =
    later2.d =
      {
        name: "day of week",
        range: 86400,
        val: function (d) {
          return d.dw || (d.dw = later2.date.getDay.call(d) + 1);
        },
        isValid: function (d, val) {
          return later2.dw.val(d) === (val || 7);
        },
        extent: function () {
          return [1, 7];
        },
        start: function (d) {
          return later2.D.start(d);
        },
        end: function (d) {
          return later2.D.end(d);
        },
        next: function (d, val) {
          val = val > 7 ? 1 : val || 7;
          return later2.date.next(
            later2.Y.val(d),
            later2.M.val(d),
            later2.D.val(d) +
              (val - later2.dw.val(d)) +
              (val <= later2.dw.val(d) ? 7 : 0),
          );
        },
        prev: function (d, val) {
          val = val > 7 ? 7 : val || 7;
          return later2.date.prev(
            later2.Y.val(d),
            later2.M.val(d),
            later2.D.val(d) +
              (val - later2.dw.val(d)) +
              (val >= later2.dw.val(d) ? -7 : 0),
          );
        },
      };
  later2.dayOfYear = later2.dy = {
    name: "day of year",
    range: 86400,
    val: function (d) {
      return (
        d.dy ||
        (d.dy = Math.ceil(
          1 +
            (later2.D.start(d).getTime() - later2.Y.start(d).getTime()) /
              later2.DAY,
        ))
      );
    },
    isValid: function (d, val) {
      return later2.dy.val(d) === (val || later2.dy.extent(d)[1]);
    },
    extent: function (d) {
      var year = later2.Y.val(d);
      return d.dyExtent || (d.dyExtent = [1, year % 4 ? 365 : 366]);
    },
    start: function (d) {
      return later2.D.start(d);
    },
    end: function (d) {
      return later2.D.end(d);
    },
    next: function (d, val) {
      val = val > later2.dy.extent(d)[1] ? 1 : val;
      var year = later2.date.nextRollover(d, val, later2.dy, later2.Y),
        dyMax = later2.dy.extent(year)[1];
      val = val > dyMax ? 1 : val || dyMax;
      return later2.date.next(later2.Y.val(year), later2.M.val(year), val);
    },
    prev: function (d, val) {
      var year = later2.date.prevRollover(d, val, later2.dy, later2.Y),
        dyMax = later2.dy.extent(year)[1];
      val = val > dyMax ? dyMax : val || dyMax;
      return later2.date.prev(later2.Y.val(year), later2.M.val(year), val);
    },
  };
  later2.hour = later2.h = {
    name: "hour",
    range: 3600,
    val: function (d) {
      return d.h || (d.h = later2.date.getHour.call(d));
    },
    isValid: function (d, val) {
      return later2.h.val(d) === val;
    },
    extent: function () {
      return [0, 23];
    },
    start: function (d) {
      return (
        d.hStart ||
        (d.hStart = later2.date.next(
          later2.Y.val(d),
          later2.M.val(d),
          later2.D.val(d),
          later2.h.val(d),
        ))
      );
    },
    end: function (d) {
      return (
        d.hEnd ||
        (d.hEnd = later2.date.prev(
          later2.Y.val(d),
          later2.M.val(d),
          later2.D.val(d),
          later2.h.val(d),
        ))
      );
    },
    next: function (d, val) {
      val = val > 23 ? 0 : val;
      var next = later2.date.next(
        later2.Y.val(d),
        later2.M.val(d),
        later2.D.val(d) + (val <= later2.h.val(d) ? 1 : 0),
        val,
      );
      if (!later2.date.isUTC && next.getTime() <= d.getTime()) {
        next = later2.date.next(
          later2.Y.val(next),
          later2.M.val(next),
          later2.D.val(next),
          val + 1,
        );
      }
      return next;
    },
    prev: function (d, val) {
      val = val > 23 ? 23 : val;
      return later2.date.prev(
        later2.Y.val(d),
        later2.M.val(d),
        later2.D.val(d) + (val >= later2.h.val(d) ? -1 : 0),
        val,
      );
    },
  };
  later2.minute = later2.m = {
    name: "minute",
    range: 60,
    val: function (d) {
      return d.m || (d.m = later2.date.getMin.call(d));
    },
    isValid: function (d, val) {
      return later2.m.val(d) === val;
    },
    extent: function (d) {
      return [0, 59];
    },
    start: function (d) {
      return (
        d.mStart ||
        (d.mStart = later2.date.next(
          later2.Y.val(d),
          later2.M.val(d),
          later2.D.val(d),
          later2.h.val(d),
          later2.m.val(d),
        ))
      );
    },
    end: function (d) {
      return (
        d.mEnd ||
        (d.mEnd = later2.date.prev(
          later2.Y.val(d),
          later2.M.val(d),
          later2.D.val(d),
          later2.h.val(d),
          later2.m.val(d),
        ))
      );
    },
    next: function (d, val) {
      var m = later2.m.val(d),
        s = later2.s.val(d),
        inc = val > 59 ? 60 - m : val <= m ? 60 - m + val : val - m,
        next = new Date(d.getTime() + inc * later2.MIN - s * later2.SEC);
      if (!later2.date.isUTC && next.getTime() <= d.getTime()) {
        next = new Date(
          d.getTime() + (inc + 120) * later2.MIN - s * later2.SEC,
        );
      }
      return next;
    },
    prev: function (d, val) {
      val = val > 59 ? 59 : val;
      return later2.date.prev(
        later2.Y.val(d),
        later2.M.val(d),
        later2.D.val(d),
        later2.h.val(d) + (val >= later2.m.val(d) ? -1 : 0),
        val,
      );
    },
  };
  later2.month = later2.M = {
    name: "month",
    range: 2629740,
    val: function (d) {
      return d.M || (d.M = later2.date.getMonth.call(d) + 1);
    },
    isValid: function (d, val) {
      return later2.M.val(d) === (val || 12);
    },
    extent: function () {
      return [1, 12];
    },
    start: function (d) {
      return (
        d.MStart ||
        (d.MStart = later2.date.next(later2.Y.val(d), later2.M.val(d)))
      );
    },
    end: function (d) {
      return (
        d.MEnd || (d.MEnd = later2.date.prev(later2.Y.val(d), later2.M.val(d)))
      );
    },
    next: function (d, val) {
      val = val > 12 ? 1 : val || 12;
      return later2.date.next(
        later2.Y.val(d) + (val > later2.M.val(d) ? 0 : 1),
        val,
      );
    },
    prev: function (d, val) {
      val = val > 12 ? 12 : val || 12;
      return later2.date.prev(
        later2.Y.val(d) - (val >= later2.M.val(d) ? 1 : 0),
        val,
      );
    },
  };
  later2.second = later2.s = {
    name: "second",
    range: 1,
    val: function (d) {
      return d.s || (d.s = later2.date.getSec.call(d));
    },
    isValid: function (d, val) {
      return later2.s.val(d) === val;
    },
    extent: function () {
      return [0, 59];
    },
    start: function (d) {
      return d;
    },
    end: function (d) {
      return d;
    },
    next: function (d, val) {
      var s = later2.s.val(d),
        inc = val > 59 ? 60 - s : val <= s ? 60 - s + val : val - s,
        next = new Date(d.getTime() + inc * later2.SEC);
      if (!later2.date.isUTC && next.getTime() <= d.getTime()) {
        next = new Date(d.getTime() + (inc + 7200) * later2.SEC);
      }
      return next;
    },
    prev: function (d, val, cache) {
      val = val > 59 ? 59 : val;
      return later2.date.prev(
        later2.Y.val(d),
        later2.M.val(d),
        later2.D.val(d),
        later2.h.val(d),
        later2.m.val(d) + (val >= later2.s.val(d) ? -1 : 0),
        val,
      );
    },
  };
  later2.time = later2.t = {
    name: "time",
    range: 1,
    val: function (d) {
      return (
        d.t ||
        (d.t = later2.h.val(d) * 3600 + later2.m.val(d) * 60 + later2.s.val(d))
      );
    },
    isValid: function (d, val) {
      return later2.t.val(d) === val;
    },
    extent: function () {
      return [0, 86399];
    },
    start: function (d) {
      return d;
    },
    end: function (d) {
      return d;
    },
    next: function (d, val) {
      val = val > 86399 ? 0 : val;
      var next = later2.date.next(
        later2.Y.val(d),
        later2.M.val(d),
        later2.D.val(d) + (val <= later2.t.val(d) ? 1 : 0),
        0,
        0,
        val,
      );
      if (!later2.date.isUTC && next.getTime() < d.getTime()) {
        next = later2.date.next(
          later2.Y.val(next),
          later2.M.val(next),
          later2.D.val(next),
          later2.h.val(next),
          later2.m.val(next),
          val + 7200,
        );
      }
      return next;
    },
    prev: function (d, val) {
      val = val > 86399 ? 86399 : val;
      return later2.date.next(
        later2.Y.val(d),
        later2.M.val(d),
        later2.D.val(d) + (val >= later2.t.val(d) ? -1 : 0),
        0,
        0,
        val,
      );
    },
  };
  later2.weekOfMonth = later2.wm = {
    name: "week of month",
    range: 604800,
    val: function (d) {
      return (
        d.wm ||
        (d.wm =
          (later2.D.val(d) +
            (later2.dw.val(later2.M.start(d)) - 1) +
            (7 - later2.dw.val(d))) /
          7)
      );
    },
    isValid: function (d, val) {
      return later2.wm.val(d) === (val || later2.wm.extent(d)[1]);
    },
    extent: function (d) {
      return (
        d.wmExtent ||
        (d.wmExtent = [
          1,
          (later2.D.extent(d)[1] +
            (later2.dw.val(later2.M.start(d)) - 1) +
            (7 - later2.dw.val(later2.M.end(d)))) /
            7,
        ])
      );
    },
    start: function (d) {
      return (
        d.wmStart ||
        (d.wmStart = later2.date.next(
          later2.Y.val(d),
          later2.M.val(d),
          Math.max(later2.D.val(d) - later2.dw.val(d) + 1, 1),
        ))
      );
    },
    end: function (d) {
      return (
        d.wmEnd ||
        (d.wmEnd = later2.date.prev(
          later2.Y.val(d),
          later2.M.val(d),
          Math.min(
            later2.D.val(d) + (7 - later2.dw.val(d)),
            later2.D.extent(d)[1],
          ),
        ))
      );
    },
    next: function (d, val) {
      val = val > later2.wm.extent(d)[1] ? 1 : val;
      var month2 = later2.date.nextRollover(d, val, later2.wm, later2.M),
        wmMax = later2.wm.extent(month2)[1];
      val = val > wmMax ? 1 : val || wmMax;
      return later2.date.next(
        later2.Y.val(month2),
        later2.M.val(month2),
        Math.max(1, (val - 1) * 7 - (later2.dw.val(month2) - 2)),
      );
    },
    prev: function (d, val) {
      var month2 = later2.date.prevRollover(d, val, later2.wm, later2.M),
        wmMax = later2.wm.extent(month2)[1];
      val = val > wmMax ? wmMax : val || wmMax;
      return later2.wm.end(
        later2.date.next(
          later2.Y.val(month2),
          later2.M.val(month2),
          Math.max(1, (val - 1) * 7 - (later2.dw.val(month2) - 2)),
        ),
      );
    },
  };
  later2.weekOfYear = later2.wy = {
    name: "week of year (ISO)",
    range: 604800,
    val: function (d) {
      if (d.wy) return d.wy;
      var wThur = later2.dw.next(later2.wy.start(d), 5),
        YThur = later2.dw.next(
          later2.Y.prev(wThur, later2.Y.val(wThur) - 1),
          5,
        );
      return (d.wy =
        1 + Math.ceil((wThur.getTime() - YThur.getTime()) / later2.WEEK));
    },
    isValid: function (d, val) {
      return later2.wy.val(d) === (val || later2.wy.extent(d)[1]);
    },
    extent: function (d) {
      if (d.wyExtent) return d.wyExtent;
      var year = later2.dw.next(later2.wy.start(d), 5),
        dwFirst = later2.dw.val(later2.Y.start(year)),
        dwLast = later2.dw.val(later2.Y.end(year));
      return (d.wyExtent = [1, dwFirst === 5 || dwLast === 5 ? 53 : 52]);
    },
    start: function (d) {
      return (
        d.wyStart ||
        (d.wyStart = later2.date.next(
          later2.Y.val(d),
          later2.M.val(d),
          later2.D.val(d) - (later2.dw.val(d) > 1 ? later2.dw.val(d) - 2 : 6),
        ))
      );
    },
    end: function (d) {
      return (
        d.wyEnd ||
        (d.wyEnd = later2.date.prev(
          later2.Y.val(d),
          later2.M.val(d),
          later2.D.val(d) + (later2.dw.val(d) > 1 ? 8 - later2.dw.val(d) : 0),
        ))
      );
    },
    next: function (d, val) {
      val = val > later2.wy.extent(d)[1] ? 1 : val;
      var wyThur = later2.dw.next(later2.wy.start(d), 5),
        year = later2.date.nextRollover(wyThur, val, later2.wy, later2.Y);
      if (later2.wy.val(year) !== 1) {
        year = later2.dw.next(year, 2);
      }
      var wyMax = later2.wy.extent(year)[1],
        wyStart = later2.wy.start(year);
      val = val > wyMax ? 1 : val || wyMax;
      return later2.date.next(
        later2.Y.val(wyStart),
        later2.M.val(wyStart),
        later2.D.val(wyStart) + 7 * (val - 1),
      );
    },
    prev: function (d, val) {
      var wyThur = later2.dw.next(later2.wy.start(d), 5),
        year = later2.date.prevRollover(wyThur, val, later2.wy, later2.Y);
      if (later2.wy.val(year) !== 1) {
        year = later2.dw.next(year, 2);
      }
      var wyMax = later2.wy.extent(year)[1],
        wyEnd = later2.wy.end(year);
      val = val > wyMax ? wyMax : val || wyMax;
      return later2.wy.end(
        later2.date.next(
          later2.Y.val(wyEnd),
          later2.M.val(wyEnd),
          later2.D.val(wyEnd) + 7 * (val - 1),
        ),
      );
    },
  };
  later2.year = later2.Y = {
    name: "year",
    range: 31556900,
    val: function (d) {
      return d.Y || (d.Y = later2.date.getYear.call(d));
    },
    isValid: function (d, val) {
      return later2.Y.val(d) === val;
    },
    extent: function () {
      return [1970, 2099];
    },
    start: function (d) {
      return d.YStart || (d.YStart = later2.date.next(later2.Y.val(d)));
    },
    end: function (d) {
      return d.YEnd || (d.YEnd = later2.date.prev(later2.Y.val(d)));
    },
    next: function (d, val) {
      return val > later2.Y.val(d) && val <= later2.Y.extent()[1]
        ? later2.date.next(val)
        : later2.NEVER;
    },
    prev: function (d, val) {
      return val < later2.Y.val(d) && val >= later2.Y.extent()[0]
        ? later2.date.prev(val)
        : later2.NEVER;
    },
  };
  later2.fullDate = later2.fd = {
    name: "full date",
    range: 1,
    val: function (d) {
      return d.fd || (d.fd = d.getTime());
    },
    isValid: function (d, val) {
      return later2.fd.val(d) === val;
    },
    extent: function () {
      return [0, 3250368e7];
    },
    start: function (d) {
      return d;
    },
    end: function (d) {
      return d;
    },
    next: function (d, val) {
      return later2.fd.val(d) < val ? new Date(val) : later2.NEVER;
    },
    prev: function (d, val) {
      return later2.fd.val(d) > val ? new Date(val) : later2.NEVER;
    },
  };
  later2.modifier = {};
  later2.modifier.after = later2.modifier.a = function (constraint, values) {
    var value = values[0];
    return {
      name: "after " + constraint.name,
      range:
        (constraint.extent(/* @__PURE__ */ new Date())[1] - value) *
        constraint.range,
      val: constraint.val,
      isValid: function (d, val) {
        return this.val(d) >= value;
      },
      extent: constraint.extent,
      start: constraint.start,
      end: constraint.end,
      next: function (startDate, val) {
        if (val != value) val = constraint.extent(startDate)[0];
        return constraint.next(startDate, val);
      },
      prev: function (startDate, val) {
        val = val === value ? constraint.extent(startDate)[1] : value - 1;
        return constraint.prev(startDate, val);
      },
    };
  };
  later2.modifier.before = later2.modifier.b = function (constraint, values) {
    var value = values[values.length - 1];
    return {
      name: "before " + constraint.name,
      range: constraint.range * (value - 1),
      val: constraint.val,
      isValid: function (d, val) {
        return this.val(d) < value;
      },
      extent: constraint.extent,
      start: constraint.start,
      end: constraint.end,
      next: function (startDate, val) {
        val = val === value ? constraint.extent(startDate)[0] : value;
        return constraint.next(startDate, val);
      },
      prev: function (startDate, val) {
        val = val === value ? value - 1 : constraint.extent(startDate)[1];
        return constraint.prev(startDate, val);
      },
    };
  };
  later2.compile = function (schedDef) {
    var constraints = [],
      constraintsLen = 0,
      tickConstraint;
    for (var key in schedDef) {
      var nameParts = key.split("_"),
        name = nameParts[0],
        mod = nameParts[1],
        vals = schedDef[key],
        constraint = mod
          ? later2.modifier[mod](later2[name], vals)
          : later2[name];
      constraints.push({
        constraint,
        vals,
      });
      constraintsLen++;
    }
    constraints.sort(function (a, b) {
      var ra = a.constraint.range,
        rb = b.constraint.range;
      return rb < ra ? -1 : rb > ra ? 1 : 0;
    });
    tickConstraint = constraints[constraintsLen - 1].constraint;
    function compareFn(dir) {
      return dir === "next"
        ? function (a, b) {
            return a.getTime() > b.getTime();
          }
        : function (a, b) {
            return b.getTime() > a.getTime();
          };
    }
    return {
      start: function (dir, startDate) {
        var next = startDate,
          nextVal = later2.array[dir],
          maxAttempts = 1e3,
          done;
        while (maxAttempts-- && !done && next) {
          done = true;
          for (var i = 0; i < constraintsLen; i++) {
            var constraint2 = constraints[i].constraint,
              curVal = constraint2.val(next),
              extent = constraint2.extent(next),
              newVal = nextVal(curVal, constraints[i].vals, extent);
            if (!constraint2.isValid(next, newVal)) {
              next = constraint2[dir](next, newVal);
              done = false;
              break;
            }
          }
        }
        if (next !== later2.NEVER) {
          next =
            dir === "next"
              ? tickConstraint.start(next)
              : tickConstraint.end(next);
        }
        return next;
      },
      end: function (dir, startDate) {
        var result,
          nextVal = later2.array[dir + "Invalid"],
          compare = compareFn(dir);
        for (var i = constraintsLen - 1; i >= 0; i--) {
          var constraint2 = constraints[i].constraint,
            curVal = constraint2.val(startDate),
            extent = constraint2.extent(startDate),
            newVal = nextVal(curVal, constraints[i].vals, extent),
            next;
          if (newVal !== void 0) {
            next = constraint2[dir](startDate, newVal);
            if (next && (!result || compare(result, next))) {
              result = next;
            }
          }
        }
        return result;
      },
      tick: function (dir, date) {
        return new Date(
          dir === "next"
            ? tickConstraint.end(date).getTime() + later2.SEC
            : tickConstraint.start(date).getTime() - later2.SEC,
        );
      },
      // PATCH
      tickSafe: function (dir, date) {
        return dir === "next"
          ? diffSecond(tickConstraint.end(date), 1)
          : diffSecond(tickConstraint.start(date), -1);
      },
      // EOF PATCH
      tickStart: function (date) {
        return tickConstraint.start(date);
      },
    };
  };
  later2.schedule = function (sched) {
    if (!sched) throw new Error("Missing schedule definition.");
    if (!sched.schedules)
      throw new Error("Definition must include at least one schedule.");
    var schedules = [],
      schedulesLen = sched.schedules.length,
      exceptions = [],
      exceptionsLen = sched.exceptions ? sched.exceptions.length : 0;
    for (var i = 0; i < schedulesLen; i++) {
      schedules.push(later2.compile(sched.schedules[i]));
    }
    for (var j = 0; j < exceptionsLen; j++) {
      exceptions.push(later2.compile(sched.exceptions[j]));
    }
    function getInstances(dir, count, startDate, endDate, isRange) {
      var compare = compareFn(dir),
        loopCount = count,
        maxAttempts = 1e6,
        schedStarts = [],
        exceptStarts = [],
        next,
        end,
        results = [],
        isForward = dir === "next",
        lastResult,
        rStart = isForward ? 0 : 1,
        rEnd = isForward ? 1 : 0;
      startDate = startDate ? new Date(startDate) : /* @__PURE__ */ new Date();
      if (!startDate || !startDate.getTime())
        throw new Error("Invalid start date.");
      setNextStarts(dir, schedules, schedStarts, startDate);
      setRangeStarts(dir, exceptions, exceptStarts, startDate);
      while (
        maxAttempts-- &&
        loopCount &&
        (next = findNext(schedStarts, compare))
      ) {
        if (endDate && compare(next, endDate)) {
          break;
        }
        if (exceptionsLen) {
          updateRangeStarts(dir, exceptions, exceptStarts, next);
          if ((end = calcRangeOverlap(dir, exceptStarts, next))) {
            updateNextStarts(dir, schedules, schedStarts, end);
            continue;
          }
        }
        if (isRange) {
          var maxEndDate = calcMaxEndDate(exceptStarts, compare);
          end = calcEnd(dir, schedules, schedStarts, next, maxEndDate);
          var r = isForward
            ? [
                new Date(Math.max(startDate, next)),
                end ? new Date(endDate ? Math.min(end, endDate) : end) : void 0,
              ]
            : [
                end
                  ? new Date(
                      endDate
                        ? Math.max(endDate, end.getTime() + later2.SEC)
                        : end.getTime() + later2.SEC,
                    )
                  : void 0,
                new Date(Math.min(startDate, next.getTime() + later2.SEC)),
              ];
          if (
            lastResult &&
            r[rStart].getTime() === lastResult[rEnd].getTime()
          ) {
            lastResult[rEnd] = r[rEnd];
            loopCount++;
          } else {
            lastResult = r;
            results.push(lastResult);
          }
          if (!end) break;
          updateNextStarts(dir, schedules, schedStarts, end);
        } else {
          results.push(
            isForward
              ? new Date(Math.max(startDate, next))
              : getStart(schedules, schedStarts, next, endDate),
          );
          tickStarts(dir, schedules, schedStarts, next);
        }
        loopCount--;
      }
      for (var i2 = 0, len = results.length; i2 < len; i2++) {
        var result = results[i2];
        results[i2] =
          Object.prototype.toString.call(result) === "[object Array]"
            ? [cleanDate(result[0]), cleanDate(result[1])]
            : cleanDate(result);
      }
      return results.length === 0
        ? later2.NEVER
        : count === 1
          ? results[0]
          : results;
    }
    function cleanDate(d) {
      if (d instanceof Date && !isNaN(d.valueOf())) {
        return new Date(d);
      }
      return void 0;
    }
    function setNextStarts(dir, schedArr, startsArr, startDate) {
      for (var i2 = 0, len = schedArr.length; i2 < len; i2++) {
        startsArr[i2] = schedArr[i2].start(dir, startDate);
      }
    }
    function updateNextStarts(dir, schedArr, startsArr, startDate) {
      var compare = compareFn(dir);
      for (var i2 = 0, len = schedArr.length; i2 < len; i2++) {
        if (startsArr[i2] && !compare(startsArr[i2], startDate)) {
          startsArr[i2] = schedArr[i2].start(dir, startDate);
        }
      }
    }
    function setRangeStarts(dir, schedArr, rangesArr, startDate) {
      var compare = compareFn(dir);
      for (var i2 = 0, len = schedArr.length; i2 < len; i2++) {
        var nextStart = schedArr[i2].start(dir, startDate);
        if (!nextStart) {
          rangesArr[i2] = later2.NEVER;
        } else {
          rangesArr[i2] = [nextStart, schedArr[i2].end(dir, nextStart)];
        }
      }
    }
    function updateRangeStarts(dir, schedArr, rangesArr, startDate) {
      var compare = compareFn(dir);
      for (var i2 = 0, len = schedArr.length; i2 < len; i2++) {
        if (rangesArr[i2] && !compare(rangesArr[i2][0], startDate)) {
          var nextStart = schedArr[i2].start(dir, startDate);
          if (!nextStart) {
            rangesArr[i2] = later2.NEVER;
          } else {
            rangesArr[i2] = [nextStart, schedArr[i2].end(dir, nextStart)];
          }
        }
      }
    }
    function tickStarts(dir, schedArr, startsArr, startDate) {
      for (var i2 = 0, len = schedArr.length; i2 < len; i2++) {
        if (startsArr[i2] && startsArr[i2].getTime() === startDate.getTime()) {
          const newStart = schedArr[i2].start(
            dir,
            schedArr[i2].tick(dir, startDate),
          );
          if (
            newStart !== later2.NEVER &&
            newStart.getTime() === startsArr[i2].getTime()
          ) {
            startsArr[i2] = schedArr[i2].start(
              dir,
              schedArr[i2].tickSafe(dir, startDate),
            );
          } else {
            startsArr[i2] = newStart;
          }
        }
      }
    }
    function getStart(schedArr, startsArr, startDate, minEndDate) {
      var result;
      for (var i2 = 0, len = startsArr.length; i2 < len; i2++) {
        if (startsArr[i2] && startsArr[i2].getTime() === startDate.getTime()) {
          var start = schedArr[i2].tickStart(startDate);
          if (minEndDate && start < minEndDate) {
            return minEndDate;
          }
          if (!result || start > result) {
            result = start;
          }
        }
      }
      return result;
    }
    function calcRangeOverlap(dir, rangesArr, startDate) {
      var compare = compareFn(dir),
        result;
      for (var i2 = 0, len = rangesArr.length; i2 < len; i2++) {
        var range = rangesArr[i2];
        if (
          range &&
          !compare(range[0], startDate) &&
          (!range[1] || compare(range[1], startDate))
        ) {
          if (!result || compare(range[1], result)) {
            result = range[1];
          }
        }
      }
      return result;
    }
    function calcMaxEndDate(exceptsArr, compare) {
      var result;
      for (var i2 = 0, len = exceptsArr.length; i2 < len; i2++) {
        if (exceptsArr[i2] && (!result || compare(result, exceptsArr[i2][0]))) {
          result = exceptsArr[i2][0];
        }
      }
      return result;
    }
    function calcEnd(dir, schedArr, startsArr, startDate, maxEndDate) {
      var compare = compareFn(dir),
        result;
      for (var i2 = 0, len = schedArr.length; i2 < len; i2++) {
        var start = startsArr[i2];
        if (start && start.getTime() === startDate.getTime()) {
          var end = schedArr[i2].end(dir, start);
          if (maxEndDate && (!end || compare(end, maxEndDate))) {
            return maxEndDate;
          }
          if (!result || compare(end, result)) {
            result = end;
          }
        }
      }
      return result;
    }
    function compareFn(dir) {
      return dir === "next"
        ? function (a, b) {
            return !b || a.getTime() > b.getTime();
          }
        : function (a, b) {
            return !a || b.getTime() > a.getTime();
          };
    }
    function findNext(arr, compare) {
      var next = arr[0];
      for (var i2 = 1, len = arr.length; i2 < len; i2++) {
        if (arr[i2] && compare(next, arr[i2])) {
          next = arr[i2];
        }
      }
      return next;
    }
    return {
      isValid: function (d) {
        return getInstances("next", 1, d, d) !== later2.NEVER;
      },
      next: function (count, startDate, endDate) {
        return getInstances("next", count || 1, startDate, endDate);
      },
      prev: function (count, startDate, endDate) {
        return getInstances("prev", count || 1, startDate, endDate);
      },
      nextRange: function (count, startDate, endDate) {
        return getInstances("next", count || 1, startDate, endDate, true);
      },
      prevRange: function (count, startDate, endDate) {
        return getInstances("prev", count || 1, startDate, endDate, true);
      },
    };
  };
  later2.setTimeout = function (fn2, sched) {
    var s = later2.schedule(sched),
      t;
    if (fn2) {
      scheduleTimeout();
    }
    function scheduleTimeout() {
      var now2 = Date.now(),
        next = s.next(2, now2);
      if (!next[0]) {
        t = void 0;
        return;
      }
      var diff = next[0].getTime() - now2;
      if (diff < 1e3) {
        diff = next[1] ? next[1].getTime() - now2 : 1e3;
      }
      if (diff < 2147483647) {
        t = setTimeout(fn2, diff);
      } else {
        t = setTimeout(scheduleTimeout, 2147483647);
      }
    }
    return {
      isDone: function () {
        return !t;
      },
      clear: function () {
        clearTimeout(t);
      },
    };
  };
  later2.setInterval = function (fn2, sched) {
    if (!fn2) {
      return;
    }
    var t = later2.setTimeout(scheduleTimeout, sched),
      done = t.isDone();
    function scheduleTimeout() {
      if (!done) {
        fn2();
        t = later2.setTimeout(scheduleTimeout, sched);
      }
    }
    return {
      isDone: function () {
        return t.isDone();
      },
      clear: function () {
        done = true;
        t.clear();
      },
    };
  };
  later2.date = {};
  later2.date.timezone = function (useLocalTime) {
    later2.date.build = useLocalTime
      ? function (Y, M, D, h, m, s) {
          return new Date(Y, M, D, h, m, s);
        }
      : function (Y, M, D, h, m, s) {
          return new Date(Date.UTC(Y, M, D, h, m, s));
        };
    var get = useLocalTime ? "get" : "getUTC",
      d = Date.prototype;
    later2.date.getYear = d[get + "FullYear"];
    later2.date.getMonth = d[get + "Month"];
    later2.date.getDate = d[get + "Date"];
    later2.date.getDay = d[get + "Day"];
    later2.date.getHour = d[get + "Hours"];
    later2.date.getMin = d[get + "Minutes"];
    later2.date.getSec = d[get + "Seconds"];
    later2.date.isUTC = !useLocalTime;
  };
  later2.date.UTC = function () {
    later2.date.timezone(false);
  };
  later2.date.localTime = function () {
    later2.date.timezone(true);
  };
  later2.date.UTC();
  later2.SEC = 1e3;
  later2.MIN = later2.SEC * 60;
  later2.HOUR = later2.MIN * 60;
  later2.DAY = later2.HOUR * 24;
  later2.WEEK = later2.DAY * 7;
  later2.DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  later2.NEVER = 0;
  later2.date.next = function (Y, M, D, h, m, s) {
    return later2.date.build(
      Y,
      M !== void 0 ? M - 1 : 0,
      D !== void 0 ? D : 1,
      h || 0,
      m || 0,
      s || 0,
    );
  };
  later2.date.nextRollover = function (d, val, constraint, period) {
    var cur = constraint.val(d),
      max = constraint.extent(d)[1];
    return (val || max) <= cur || val > max
      ? new Date(period.end(d).getTime() + later2.SEC)
      : period.start(d);
  };
  later2.date.prev = function (Y, M, D, h, m, s) {
    var len = arguments.length;
    M = len < 2 ? 11 : M - 1;
    D = len < 3 ? later2.D.extent(later2.date.next(Y, M + 1))[1] : D;
    h = len < 4 ? 23 : h;
    m = len < 5 ? 59 : m;
    s = len < 6 ? 59 : s;
    return later2.date.build(Y, M, D, h, m, s);
  };
  later2.date.prevRollover = function (d, val, constraint, period) {
    var cur = constraint.val(d);
    return val >= cur || !val
      ? period.start(period.prev(d, period.val(d) - 1))
      : period.start(d);
  };
  later2.parse = {};
  later2.parse.cron = function (expr, hasSeconds) {
    var NAMES = {
      JAN: 1,
      FEB: 2,
      MAR: 3,
      APR: 4,
      MAY: 5,
      JUN: 6,
      JUL: 7,
      AUG: 8,
      SEP: 9,
      OCT: 10,
      NOV: 11,
      DEC: 12,
      SUN: 1,
      MON: 2,
      TUE: 3,
      WED: 4,
      THU: 5,
      FRI: 6,
      SAT: 7,
    };
    var REPLACEMENTS = {
      "* * * * * *": "0/1 * * * * *",
      "@YEARLY": "0 0 1 1 *",
      "@ANNUALLY": "0 0 1 1 *",
      "@MONTHLY": "0 0 1 * *",
      "@WEEKLY": "0 0 * * 0",
      "@DAILY": "0 0 * * *",
      "@HOURLY": "0 * * * *",
    };
    var FIELDS = {
      s: [0, 0, 59],
      m: [1, 0, 59],
      h: [2, 0, 23],
      D: [3, 1, 31],
      M: [4, 1, 12],
      Y: [6, 1970, 2099],
      d: [5, 1, 7, 1],
    };
    function getValue(value, offset, max) {
      return isNaN(value)
        ? NAMES[value] || null
        : Math.min(+value + (offset || 0), max || 9999);
    }
    function cloneSchedule(sched) {
      var clone = {},
        field2;
      for (field2 in sched) {
        if (field2 !== "dc" && field2 !== "d") {
          clone[field2] = sched[field2].slice(0);
        }
      }
      return clone;
    }
    function add(sched, name, min2, max, inc) {
      var i = min2;
      if (!sched[name]) {
        sched[name] = [];
      }
      while (i <= max) {
        if (sched[name].indexOf(i) < 0) {
          sched[name].push(i);
        }
        i += inc || 1;
      }
      sched[name].sort(function (a, b) {
        return a - b;
      });
    }
    function addHash(schedules, curSched, value, hash) {
      if (
        (curSched.d && !curSched.dc) ||
        (curSched.dc && curSched.dc.indexOf(hash) < 0)
      ) {
        schedules.push(cloneSchedule(curSched));
        curSched = schedules[schedules.length - 1];
      }
      add(curSched, "d", value, value);
      add(curSched, "dc", hash, hash);
    }
    function addWeekday(s, curSched, value) {
      var except1 = {},
        except2 = {};
      if (value === 1) {
        add(curSched, "D", 1, 3);
        add(curSched, "d", NAMES.MON, NAMES.FRI);
        add(except1, "D", 2, 2);
        add(except1, "d", NAMES.TUE, NAMES.FRI);
        add(except2, "D", 3, 3);
        add(except2, "d", NAMES.TUE, NAMES.FRI);
      } else {
        add(curSched, "D", value - 1, value + 1);
        add(curSched, "d", NAMES.MON, NAMES.FRI);
        add(except1, "D", value - 1, value - 1);
        add(except1, "d", NAMES.MON, NAMES.THU);
        add(except2, "D", value + 1, value + 1);
        add(except2, "d", NAMES.TUE, NAMES.FRI);
      }
      s.exceptions.push(except1);
      s.exceptions.push(except2);
    }
    function addRange(item, curSched, name, min2, max, offset) {
      var incSplit = item.split("/"),
        inc = +incSplit[1],
        range = incSplit[0];
      if (range !== "*" && range !== "0") {
        var rangeSplit = range.split("-");
        min2 = getValue(rangeSplit[0], offset, max);
        max = getValue(rangeSplit[1], offset, max) || max;
      }
      add(curSched, name, min2, max, inc);
    }
    function parse(item, s, name, min2, max, offset) {
      var value,
        split2,
        schedules = s.schedules,
        curSched = schedules[schedules.length - 1];
      if (item === "L") {
        item = min2 - 1;
      }
      if ((value = getValue(item, offset, max)) !== null) {
        add(curSched, name, value, value);
      } else if (
        (value = getValue(item.replace("W", ""), offset, max)) !== null
      ) {
        addWeekday(s, curSched, value);
      } else if (
        (value = getValue(item.replace("L", ""), offset, max)) !== null
      ) {
        addHash(schedules, curSched, value, min2 - 1);
      } else if ((split2 = item.split("#")).length === 2) {
        value = getValue(split2[0], offset, max);
        addHash(schedules, curSched, value, getValue(split2[1]));
      } else {
        addRange(item, curSched, name, min2, max, offset);
      }
    }
    function isHash(item) {
      return item.indexOf("#") > -1 || item.indexOf("L") > 0;
    }
    function itemSorter(a, b) {
      return isHash(a) && !isHash(b) ? 1 : a - b;
    }
    function parseExpr(expr2) {
      var schedule = {
          schedules: [{}],
          exceptions: [],
        },
        components = expr2.replace(/(\s)+/g, " ").split(" "),
        field2,
        f,
        component,
        items2;
      for (field2 in FIELDS) {
        f = FIELDS[field2];
        component = components[f[0]];
        if (component && component !== "*" && component !== "?") {
          items2 = component.split(",").sort(itemSorter);
          var i,
            length = items2.length;
          for (i = 0; i < length; i++) {
            parse(items2[i], schedule, field2, f[1], f[2], f[3]);
          }
        }
      }
      return schedule;
    }
    function prepareExpr(expr2) {
      var prepared = expr2.toUpperCase();
      return REPLACEMENTS[prepared] || prepared;
    }
    var e = prepareExpr(expr);
    return parseExpr(hasSeconds ? e : "0 " + e);
  };
  later2.parse.recur = function () {
    var schedules = [],
      exceptions = [],
      cur,
      curArr = schedules,
      curName,
      values,
      every2,
      modifier,
      applyMin,
      applyMax,
      i,
      last;
    function add(name, min2, max) {
      name = modifier ? name + "_" + modifier : name;
      if (!cur) {
        curArr.push({});
        cur = curArr[0];
      }
      if (!cur[name]) {
        cur[name] = [];
      }
      curName = cur[name];
      if (every2) {
        values = [];
        for (i = min2; i <= max; i += every2) {
          values.push(i);
        }
        last = {
          n: name,
          x: every2,
          c: curName.length,
          m: max,
        };
      }
      values = applyMin ? [min2] : applyMax ? [max] : values;
      var length = values.length;
      for (i = 0; i < length; i += 1) {
        var val = values[i];
        if (curName.indexOf(val) < 0) {
          curName.push(val);
        }
      }
      values = every2 = modifier = applyMin = applyMax = 0;
    }
    return {
      schedules,
      exceptions,
      on: function () {
        values = arguments[0] instanceof Array ? arguments[0] : arguments;
        return this;
      },
      every: function (x) {
        every2 = x || 1;
        return this;
      },
      after: function (x) {
        modifier = "a";
        values = [x];
        return this;
      },
      before: function (x) {
        modifier = "b";
        values = [x];
        return this;
      },
      first: function () {
        applyMin = 1;
        return this;
      },
      last: function () {
        applyMax = 1;
        return this;
      },
      time: function () {
        for (var i2 = 0, len = values.length; i2 < len; i2++) {
          var split2 = values[i2].split(":");
          if (split2.length < 3) split2.push(0);
          values[i2] = +split2[0] * 3600 + +split2[1] * 60 + +split2[2];
        }
        add("t");
        return this;
      },
      second: function () {
        add("s", 0, 59);
        return this;
      },
      minute: function () {
        add("m", 0, 59);
        return this;
      },
      hour: function () {
        add("h", 0, 23);
        return this;
      },
      dayOfMonth: function () {
        add("D", 1, applyMax ? 0 : 31);
        return this;
      },
      dayOfWeek: function () {
        add("d", 1, 7);
        return this;
      },
      onWeekend: function () {
        values = [1, 7];
        return this.dayOfWeek();
      },
      onWeekday: function () {
        values = [2, 3, 4, 5, 6];
        return this.dayOfWeek();
      },
      dayOfWeekCount: function () {
        add("dc", 1, applyMax ? 0 : 5);
        return this;
      },
      dayOfYear: function () {
        add("dy", 1, applyMax ? 0 : 366);
        return this;
      },
      weekOfMonth: function () {
        add("wm", 1, applyMax ? 0 : 5);
        return this;
      },
      weekOfYear: function () {
        add("wy", 1, applyMax ? 0 : 53);
        return this;
      },
      month: function () {
        add("M", 1, 12);
        return this;
      },
      year: function () {
        add("Y", 1970, 2450);
        return this;
      },
      fullDate: function () {
        for (var i2 = 0, len = values.length; i2 < len; i2++) {
          values[i2] = values[i2].getTime();
        }
        add("fd");
        return this;
      },
      customModifier: function (id, vals) {
        var custom = later2.modifier[id];
        if (!custom)
          throw new Error("Custom modifier " + id + " not recognized!");
        modifier = id;
        values = arguments[1] instanceof Array ? arguments[1] : [arguments[1]];
        return this;
      },
      customPeriod: function (id) {
        var custom = later2[id];
        if (!custom)
          throw new Error("Custom time period " + id + " not recognized!");
        add(
          id,
          custom.extent(/* @__PURE__ */ new Date())[0],
          custom.extent(/* @__PURE__ */ new Date())[1],
        );
        return this;
      },
      startingOn: function (start) {
        return this.between(start, last.m);
      },
      between: function (start, end) {
        cur[last.n] = cur[last.n].splice(0, last.c);
        every2 = last.x;
        add(last.n, start, end);
        return this;
      },
      and: function () {
        cur = curArr[curArr.push({}) - 1];
        return this;
      },
      except: function () {
        curArr = exceptions;
        cur = null;
        return this;
      },
    };
  };
  later2.parse.text = function (str) {
    var recur = later2.parse.recur,
      pos = 0,
      input = "",
      error;
    var TOKENTYPES = {
      eof: /^$/,
      fullDate: /^(\d\d\d\d-\d\d-\d\dt\d\d:\d\d:\d\d)\b/,
      rank: /^((\d\d\d\d)|([2-5]?1(st)?|[2-5]?2(nd)?|[2-5]?3(rd)?|(0|[1-5]?[4-9]|[1-5]0|1[1-3])(th)?))\b/,
      time: /^((([0]?[1-9]|1[0-2]):[0-5]\d(\s)?(am|pm))|(([0]?\d|1\d|2[0-3]):[0-5]\d))\b/,
      dayName:
        /^((sun|mon|tue(s)?|wed(nes)?|thu(r(s)?)?|fri|sat(ur)?)(day)?)\b/,
      monthName:
        /^(jan(uary)?|feb(ruary)?|ma((r(ch)?)?|y)|apr(il)?|ju(ly|ne)|aug(ust)?|oct(ober)?|(sept|nov|dec)(ember)?)\b/,
      yearIndex: /^(\d\d\d\d)\b/,
      every: /^every\b/,
      after: /^after\b/,
      before: /^before\b/,
      second: /^(s|sec(ond)?(s)?)\b/,
      minute: /^(m|min(ute)?(s)?)\b/,
      hour: /^(h|hour(s)?)\b/,
      day: /^(day(s)?( of the month)?)\b/,
      dayInstance: /^day instance\b/,
      dayOfWeek: /^day(s)? of the week\b/,
      dayOfYear: /^day(s)? of the year\b/,
      weekOfYear: /^week(s)?( of the year)?\b/,
      weekOfMonth: /^week(s)? of the month\b/,
      weekday: /^weekday\b/,
      weekend: /^weekend\b/,
      month: /^month(s)?\b/,
      year: /^year(s)?\b/,
      between: /^between (the)?\b/,
      start: /^(start(ing)? (at|on( the)?)?)\b/,
      at: /^(at|@)\b/,
      and: /^(,|and\b)/,
      except: /^(except\b)/,
      also: /(also)\b/,
      first: /^(first)\b/,
      last: /^last\b/,
      in: /^in\b/,
      of: /^of\b/,
      onthe: /^on the\b/,
      on: /^on\b/,
      through: /(-|^(to|through)\b)/,
    };
    var NAMES = {
      jan: 1,
      feb: 2,
      mar: 3,
      apr: 4,
      may: 5,
      jun: 6,
      jul: 7,
      aug: 8,
      sep: 9,
      oct: 10,
      nov: 11,
      dec: 12,
      sun: 1,
      mon: 2,
      tue: 3,
      wed: 4,
      thu: 5,
      fri: 6,
      sat: 7,
      "1st": 1,
      fir: 1,
      "2nd": 2,
      sec: 2,
      "3rd": 3,
      thi: 3,
      "4th": 4,
      for: 4,
    };
    function t(start, end, text, type) {
      return {
        startPos: start,
        endPos: end,
        text,
        type,
      };
    }
    function peek(expected) {
      var scanTokens = expected instanceof Array ? expected : [expected],
        whiteSpace = /\s+/,
        token,
        curInput,
        m,
        scanToken,
        start,
        len;
      scanTokens.push(whiteSpace);
      start = pos;
      while (!token || token.type === whiteSpace) {
        len = -1;
        curInput = input.substring(start);
        token = t(start, start, input.split(whiteSpace)[0]);
        var i,
          length = scanTokens.length;
        for (i = 0; i < length; i++) {
          scanToken = scanTokens[i];
          m = scanToken.exec(curInput);
          if (m && m.index === 0 && m[0].length > len) {
            len = m[0].length;
            token = t(
              start,
              start + len,
              curInput.substring(0, len),
              scanToken,
            );
          }
        }
        if (token.type === whiteSpace) {
          start = token.endPos;
        }
      }
      return token;
    }
    function scan(expectedToken) {
      var token = peek(expectedToken);
      pos = token.endPos;
      return token;
    }
    function parseThroughExpr(tokenType) {
      var start = +parseTokenValue(tokenType),
        end = checkAndParse(TOKENTYPES.through)
          ? +parseTokenValue(tokenType)
          : start,
        nums = [];
      for (var i = start; i <= end; i++) {
        nums.push(i);
      }
      return nums;
    }
    function parseRanges(tokenType) {
      var nums = parseThroughExpr(tokenType);
      while (checkAndParse(TOKENTYPES.and)) {
        nums.push.apply(nums, parseThroughExpr(tokenType));
      }
      if (tokenType === TOKENTYPES.dayName) {
        nums.sort((a, b) => a - b);
      }
      return nums;
    }
    function parseEvery(r) {
      var num, period, start, end;
      if (checkAndParse(TOKENTYPES.weekend)) {
        r.on(NAMES.sun, NAMES.sat).dayOfWeek();
      } else if (checkAndParse(TOKENTYPES.weekday)) {
        r.on(NAMES.mon, NAMES.tue, NAMES.wed, NAMES.thu, NAMES.fri).dayOfWeek();
      } else {
        num = parseTokenValue(TOKENTYPES.rank);
        r.every(num);
        period = parseTimePeriod(r);
        if (checkAndParse(TOKENTYPES.start)) {
          num = parseTokenValue(TOKENTYPES.rank);
          r.startingOn(num);
          parseToken(period.type);
        } else if (checkAndParse(TOKENTYPES.between)) {
          start = parseTokenValue(TOKENTYPES.rank);
          if (checkAndParse(TOKENTYPES.and)) {
            end = parseTokenValue(TOKENTYPES.rank);
            r.between(start, end);
          }
        }
      }
    }
    function parseOnThe(r) {
      if (checkAndParse(TOKENTYPES.first)) {
        r.first();
      } else if (checkAndParse(TOKENTYPES.last)) {
        r.last();
      } else {
        r.on(parseRanges(TOKENTYPES.rank));
      }
      parseTimePeriod(r);
    }
    function parseScheduleExpr(str2) {
      pos = 0;
      input = str2;
      error = -1;
      var r = recur();
      while (pos < input.length && error < 0) {
        var token = parseToken([
          TOKENTYPES.every,
          TOKENTYPES.after,
          TOKENTYPES.before,
          TOKENTYPES.onthe,
          TOKENTYPES.on,
          TOKENTYPES.of,
          TOKENTYPES["in"],
          TOKENTYPES.at,
          TOKENTYPES.and,
          TOKENTYPES.except,
          TOKENTYPES.also,
        ]);
        switch (token.type) {
          case TOKENTYPES.every:
            parseEvery(r);
            break;
          case TOKENTYPES.after:
            if (peek(TOKENTYPES.time).type !== void 0) {
              r.after(parseTokenValue(TOKENTYPES.time));
              r.time();
            } else if (peek(TOKENTYPES.fullDate).type !== void 0) {
              r.after(parseTokenValue(TOKENTYPES.fullDate));
              r.fullDate();
            } else {
              r.after(parseTokenValue(TOKENTYPES.rank));
              parseTimePeriod(r);
            }
            break;
          case TOKENTYPES.before:
            if (peek(TOKENTYPES.time).type !== void 0) {
              r.before(parseTokenValue(TOKENTYPES.time));
              r.time();
            } else if (peek(TOKENTYPES.fullDate).type !== void 0) {
              r.before(parseTokenValue(TOKENTYPES.fullDate));
              r.fullDate();
            } else {
              r.before(parseTokenValue(TOKENTYPES.rank));
              parseTimePeriod(r);
            }
            break;
          case TOKENTYPES.onthe:
            parseOnThe(r);
            break;
          case TOKENTYPES.on:
            r.on(parseRanges(TOKENTYPES.dayName)).dayOfWeek();
            break;
          case TOKENTYPES.of:
            r.on(parseRanges(TOKENTYPES.monthName)).month();
            break;
          case TOKENTYPES["in"]:
            r.on(parseRanges(TOKENTYPES.yearIndex)).year();
            break;
          case TOKENTYPES.at:
            r.on(parseTokenValue(TOKENTYPES.time)).time();
            while (checkAndParse(TOKENTYPES.and)) {
              r.on(parseTokenValue(TOKENTYPES.time)).time();
            }
            break;
          case TOKENTYPES.and:
            break;
          case TOKENTYPES.also:
            r.and();
            break;
          case TOKENTYPES.except:
            r.except();
            break;
          default:
            error = pos;
        }
      }
      return {
        schedules: r.schedules,
        exceptions: r.exceptions,
        error,
      };
    }
    function parseTimePeriod(r) {
      var timePeriod = parseToken([
        TOKENTYPES.second,
        TOKENTYPES.minute,
        TOKENTYPES.hour,
        TOKENTYPES.dayOfYear,
        TOKENTYPES.dayOfWeek,
        TOKENTYPES.dayInstance,
        TOKENTYPES.day,
        TOKENTYPES.month,
        TOKENTYPES.year,
        TOKENTYPES.weekOfMonth,
        TOKENTYPES.weekOfYear,
      ]);
      switch (timePeriod.type) {
        case TOKENTYPES.second:
          r.second();
          break;
        case TOKENTYPES.minute:
          r.minute();
          break;
        case TOKENTYPES.hour:
          r.hour();
          break;
        case TOKENTYPES.dayOfYear:
          r.dayOfYear();
          break;
        case TOKENTYPES.dayOfWeek:
          r.dayOfWeek();
          break;
        case TOKENTYPES.dayInstance:
          r.dayOfWeekCount();
          break;
        case TOKENTYPES.day:
          r.dayOfMonth();
          break;
        case TOKENTYPES.weekOfMonth:
          r.weekOfMonth();
          break;
        case TOKENTYPES.weekOfYear:
          r.weekOfYear();
          break;
        case TOKENTYPES.month:
          r.month();
          break;
        case TOKENTYPES.year:
          r.year();
          break;
        default:
          error = pos;
      }
      return timePeriod;
    }
    function checkAndParse(tokenType) {
      var found = peek(tokenType).type === tokenType;
      if (found) {
        scan(tokenType);
      }
      return found;
    }
    function parseToken(tokenType) {
      var t2 = scan(tokenType);
      if (t2.type) {
        t2.text = convertString(t2.text, tokenType);
      } else {
        error = pos;
      }
      return t2;
    }
    function parseTokenValue(tokenType) {
      return parseToken(tokenType).text;
    }
    function convertString(str2, tokenType) {
      var output = str2;
      switch (tokenType) {
        case TOKENTYPES.time:
          var parts = str2.split(/(:|am|pm)/),
            hour2 =
              parts[3] === "pm" && parts[0] < 12
                ? parseInt(parts[0], 10) + 12
                : parts[0],
            min2 = parts[2].trim();
          output = (hour2.length === 1 ? "0" : "") + hour2 + ":" + min2;
          break;
        case TOKENTYPES.rank:
          output = parseInt(/^\d+/.exec(str2)[0], 10);
          break;
        case TOKENTYPES.monthName:
        case TOKENTYPES.dayName:
          output = NAMES[str2.substring(0, 3)];
          break;
        case TOKENTYPES.fullDate:
          output = new Date(str2.toUpperCase());
          break;
      }
      return output;
    }
    return parseScheduleExpr(str.toLowerCase());
  };
  return later2;
})();
later.date.localTime();
var later_default = later;

// ../Engine/lib/Engine/calendar/CalendarIntervalMixin.js
var CalendarIntervalMixin = class extends Mixin(
  [AbstractPartOfProjectModelMixin],
  (base) => {
    const superProto = base.prototype;
    class CalendarIntervalMixin2 extends base {
      static get fields() {
        return [
          "name",
          { name: "startDate", type: "date" },
          { name: "endDate", type: "date" },
          "recurrentStartDate",
          "recurrentEndDate",
          "cls",
          "iconCls",
          { name: "isWorking", type: "boolean", defaultValue: false },
          { name: "priority", type: "number" },
        ];
      }
      getCalendar() {
        return this.stores[0].calendar;
      }
      resetPriority() {
        this.priorityField = null;
        this.getCalendar().getDepth();
      }
      // not just `getPriority` to avoid clash with auto-generated getter in the subclasses
      getPriorityField() {
        if (this.priorityField != null) return this.priorityField;
        let base2 = 1e4 + this.getCalendar().getDepth() * 100;
        let priority = this.priority;
        if (priority == null) {
          priority = this.isRecurrent() ? 20 : 30;
        }
        return (this.priorityField = base2 + priority);
      }
      /**
       * Whether this interval is recurrent (both [[recurrentStartDate]] and [[recurrentEndDate]] are present and parsed correctly
       * by the `later` library)
       */
      isRecurrent() {
        return Boolean(
          this.recurrentStartDate &&
          this.recurrentEndDate &&
          this.getStartDateSchedule() &&
          this.getEndDateSchedule(),
        );
      }
      /**
       * Whether this interval is static - both [[startDate]] and [[endDate]] are present.
       */
      isStatic() {
        return Boolean(this.startDate && this.endDate);
      }
      /**
       * Helper method to parse [[recurrentStartDate]] and [[recurrentEndDate]] field values.
       * @param {Object|String} schedule Recurrence schedule
       * @returns {Object} Processed schedule ready to be used by later.schedule() method.
       * @private
       */
      parseDateSchedule(value) {
        let schedule = value;
        if (value && value !== Object(value)) {
          schedule = later_default.parse.text(value);
          if (schedule !== Object(schedule) || schedule.error >= 0) {
            try {
              schedule = JSON.parse(value);
            } catch (e) {
              return null;
            }
          }
        }
        return schedule;
      }
      getStartDateSchedule() {
        if (this.startDateSchedule) return this.startDateSchedule;
        const schedule = this.parseDateSchedule(this.recurrentStartDate);
        return (this.startDateSchedule = later_default.schedule(schedule));
      }
      getEndDateSchedule() {
        if (this.endDateSchedule) return this.endDateSchedule;
        if (this.recurrentEndDate === "EOD") return "EOD";
        const schedule = this.parseDateSchedule(this.recurrentEndDate);
        return (this.endDateSchedule = later_default.schedule(schedule));
      }
    }
    return CalendarIntervalMixin2;
  },
) {};

// ../Engine/lib/Engine/calendar/CalendarIntervalStore.js
var CalendarIntervalStore = class extends Mixin(
  [AbstractPartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class CalendarIntervalStore2 extends base {
      constructor() {
        super(...arguments);
        this.disableHasLoadedDataToCommitFlag = true;
      }
      static get defaultConfig() {
        return {
          modelClass: CalendarIntervalMixin,
        };
      }
    }
    return CalendarIntervalStore2;
  },
) {};

// ../Engine/lib/Engine/scheduling/Types.js
var TimeUnit;
(function (TimeUnit2) {
  TimeUnit2["Millisecond"] = "millisecond";
  TimeUnit2["Second"] = "second";
  TimeUnit2["Minute"] = "minute";
  TimeUnit2["Hour"] = "hour";
  TimeUnit2["Day"] = "day";
  TimeUnit2["Week"] = "week";
  TimeUnit2["Month"] = "month";
  TimeUnit2["Quarter"] = "quarter";
  TimeUnit2["Year"] = "year";
})(TimeUnit || (TimeUnit = {}));
var ProjectConstraintResolution;
(function (ProjectConstraintResolution2) {
  ProjectConstraintResolution2["Honor"] = "honor";
  ProjectConstraintResolution2["Ignore"] = "ignore";
  ProjectConstraintResolution2["Conflict"] = "conflict";
})(ProjectConstraintResolution || (ProjectConstraintResolution = {}));
var ConstraintType;
(function (ConstraintType2) {
  ConstraintType2["MustStartOn"] = "muststarton";
  ConstraintType2["MustFinishOn"] = "mustfinishon";
  ConstraintType2["StartNoEarlierThan"] = "startnoearlierthan";
  ConstraintType2["StartNoLaterThan"] = "startnolaterthan";
  ConstraintType2["FinishNoEarlierThan"] = "finishnoearlierthan";
  ConstraintType2["FinishNoLaterThan"] = "finishnolaterthan";
  ConstraintType2["AsSoonAsPossible"] = "assoonaspossible";
  ConstraintType2["AsLateAsPossible"] = "aslateaspossible";
})(ConstraintType || (ConstraintType = {}));
var SchedulingMode;
(function (SchedulingMode2) {
  SchedulingMode2["Normal"] = "Normal";
  SchedulingMode2["FixedDuration"] = "FixedDuration";
  SchedulingMode2["FixedEffort"] = "FixedEffort";
  SchedulingMode2["FixedUnits"] = "FixedUnits";
})(SchedulingMode || (SchedulingMode = {}));
var DependencyValidationResult;
(function (DependencyValidationResult2) {
  DependencyValidationResult2[(DependencyValidationResult2["NoError"] = 0)] =
    "NoError";
  DependencyValidationResult2[
    (DependencyValidationResult2["CyclicDependency"] = 1)
  ] = "CyclicDependency";
  DependencyValidationResult2[
    (DependencyValidationResult2["DuplicatingDependency"] = 2)
  ] = "DuplicatingDependency";
})(DependencyValidationResult || (DependencyValidationResult = {}));
var DependencyType;
(function (DependencyType2) {
  DependencyType2[(DependencyType2["StartToStart"] = 0)] = "StartToStart";
  DependencyType2[(DependencyType2["StartToEnd"] = 1)] = "StartToEnd";
  DependencyType2[(DependencyType2["EndToStart"] = 2)] = "EndToStart";
  DependencyType2[(DependencyType2["EndToEnd"] = 3)] = "EndToEnd";
})(DependencyType || (DependencyType = {}));
var DependenciesCalendar;
(function (DependenciesCalendar2) {
  DependenciesCalendar2["Project"] = "Project";
  DependenciesCalendar2["FromEvent"] = "FromEvent";
  DependenciesCalendar2["ToEvent"] = "ToEvent";
})(DependenciesCalendar || (DependenciesCalendar = {}));
var ProjectType;
(function (ProjectType2) {
  ProjectType2[(ProjectType2["SchedulerBasic"] = 1)] = "SchedulerBasic";
  ProjectType2[(ProjectType2["SchedulerPro"] = 2)] = "SchedulerPro";
  ProjectType2[(ProjectType2["Gantt"] = 3)] = "Gantt";
})(ProjectType || (ProjectType = {}));
var Direction;
(function (Direction2) {
  Direction2["Forward"] = "Forward";
  Direction2["Backward"] = "Backward";
  Direction2["None"] = "None";
})(Direction || (Direction = {}));
var isEqualEffectiveDirection = (a, b) => {
  if ((a && !b) || (!a && b)) return false;
  if (!a && !b) return true;
  return (
    a.direction === b.direction &&
    ((a.kind === "own" && b.kind === "own") ||
      (a.kind === "enforced" &&
        b.kind === "enforced" &&
        a.enforcedBy === b.enforcedBy) ||
      (a.kind === "inherited" &&
        b.kind === "inherited" &&
        a.inheritedFrom === b.inheritedFrom))
  );
};
var ConstraintIntervalSide;
(function (ConstraintIntervalSide2) {
  ConstraintIntervalSide2["Start"] = "Start";
  ConstraintIntervalSide2["End"] = "End";
})(ConstraintIntervalSide || (ConstraintIntervalSide = {}));

// ../Engine/lib/Engine/util/Constants.js
var MIN_DATE = /* @__PURE__ */ new Date(-864e13);
var MAX_DATE = /* @__PURE__ */ new Date(864e13);
var isDateFinite = (date) => {
  if (!date) return false;
  const time = date.getTime();
  return time !== MIN_DATE.getTime() && time !== MAX_DATE.getTime();
};

// ../Engine/lib/Engine/util/Types.js
var EdgeInclusion;
(function (EdgeInclusion2) {
  EdgeInclusion2[(EdgeInclusion2["Left"] = 0)] = "Left";
  EdgeInclusion2[(EdgeInclusion2["Right"] = 1)] = "Right";
})(EdgeInclusion || (EdgeInclusion = {}));

// ../Engine/lib/Engine/calendar/CalendarCache.js
var CalendarIteratorResult;
(function (CalendarIteratorResult2) {
  CalendarIteratorResult2[(CalendarIteratorResult2["FullRangeIterated"] = 0)] =
    "FullRangeIterated";
  CalendarIteratorResult2[(CalendarIteratorResult2["StoppedByIterator"] = 1)] =
    "StoppedByIterator";
  CalendarIteratorResult2[
    (CalendarIteratorResult2["MaxCacheExtendCyclesReached"] = 2)
  ] = "MaxCacheExtendCyclesReached";
  CalendarIteratorResult2[(CalendarIteratorResult2["MaxRangeReached"] = 3)] =
    "MaxRangeReached";
})(CalendarIteratorResult || (CalendarIteratorResult = {}));
var CalendarCache = class {
  constructor(config) {
    this.cacheFilledStartDate = MAX_DATE;
    this.cacheFilledEndDate = MIN_DATE;
    this.intervalsCachingChunkDuration = 30;
    this.intervalsCachingChunkUnit = TimeUnit.Day;
    this.maxCacheExtendCycles = 1e3;
    this.maxRange = 5 * 365 * 24 * 60 * 60 * 1e3;
    config && Object.assign(this, config);
  }
  includeWrappingRangeFrom(cache, startDate, endDate) {
    cache.ensureCacheFilledForInterval(startDate, endDate);
    this.intervalCache.includeWrappingRange(
      cache.intervalCache,
      startDate,
      endDate,
    );
  }
  // after this method, we guarantee, that for every point between `startDate` and `endDate` (_inclusive_)
  // we'll have a final representation of the cache, that is, we'll be able to get an interval to which this point belongs
  // _both_ for forward and backward directions
  ensureCacheFilledForInterval(startDate, endDate) {
    const cacheFilledStartDateN = this.cacheFilledStartDate.getTime();
    const cacheFilledEndDateN = this.cacheFilledEndDate.getTime();
    if (cacheFilledStartDateN !== MAX_DATE.getTime()) {
      const startDateN = startDate.getTime();
      const endDateN = endDate.getTime();
      if (
        cacheFilledStartDateN <= startDateN &&
        endDateN <= cacheFilledEndDateN
      )
        return;
      if (endDateN <= cacheFilledStartDateN) {
        endDate = new Date(cacheFilledStartDateN - 1);
      } else if (startDateN >= cacheFilledEndDateN) {
        startDate = new Date(cacheFilledEndDateN);
      } else if (
        cacheFilledStartDateN <= startDateN &&
        startDateN <= cacheFilledEndDateN
      ) {
        startDate = new Date(cacheFilledEndDateN + 1);
      } else if (
        cacheFilledStartDateN <= endDateN &&
        endDateN <= cacheFilledEndDateN
      ) {
        endDate = new Date(cacheFilledStartDateN - 1);
      } else {
        this.ensureCacheFilledForInterval(
          startDate,
          new Date(cacheFilledStartDateN - 1),
        );
        this.ensureCacheFilledForInterval(
          new Date(cacheFilledEndDateN + 1),
          endDate,
        );
        return;
      }
    }
    if (
      cacheFilledStartDateN === MAX_DATE.getTime() ||
      startDate.getTime() < cacheFilledEndDateN
    ) {
      this.cacheFilledStartDate = startDate;
    }
    if (
      cacheFilledEndDateN === MIN_DATE.getTime() ||
      cacheFilledEndDateN < endDate.getTime()
    ) {
      this.cacheFilledEndDate = endDate;
    }
    this.fillCache(startDate, endDate);
  }
  fillCache(_1, _2) {
    throw new Error("Abstract method");
  }
  clear() {
    this.cacheFilledStartDate = MAX_DATE;
    this.cacheFilledEndDate = MIN_DATE;
    this.intervalCache.clear();
  }
  /**
   * The core iterator method of the calendar cache.
   *
   * @param options The options for iterator. Should contain at least one of the `startDate`/`endDate` properties
   * which indicates what timespan to examine for availability intervals. If one of boundaries is not provided
   * iterator function should return `false` at some point, to avoid infinite loops.
   *
   * Another recognized option is `isForward`, which indicates the direction in which to iterate through the timespan.
   *
   * Another recognized option is `maxRange`, which indicates the maximum timespan for this iterator (in milliseconds). When iterator
   * exceeds this timespan, the iteration is stopped and [[CalendarIteratorResult.MaxRangeReached]] value is returned.
   * Default value is 5 years.
   *
   * @param func The iterator function to call. It will be called for every distinct set of availability intervals, found
   * in the given timespan. All the intervals, which are "active" for current interval are collected in the 3rd argument
   * for this function. If iterator returns `false` (checked with `===`) the iteration stops.
   *
   * @param scope The scope (`this` value) to execute the iterator in.
   */
  forEachAvailabilityInterval(options, func, scope) {
    var _a4;
    scope = scope || this;
    const startDate = options.startDate;
    const endDate = options.endDate;
    const startDateN = startDate && startDate.getTime();
    const endDateN = endDate && endDate.getTime();
    const maxRange = (_a4 = options.maxRange) != null ? _a4 : this.maxRange;
    const isForward = options.isForward !== false;
    if (isForward ? !startDate : !endDate) {
      throw new Error(
        "At least `startDate` or `endDate` is required, depending from the `isForward` option",
      );
    }
    const intervalCache = this.intervalCache;
    let cacheCursorDate = isForward ? startDate : endDate;
    let cursorDate = isForward ? startDate : endDate;
    const rangeStart = cursorDate.getTime();
    for (let cycle = 1; cycle < this.maxCacheExtendCycles; cycle++) {
      if (isForward) {
        this.ensureCacheFilledForInterval(
          cacheCursorDate,
          endDate ||
            DateHelper.add(
              cacheCursorDate,
              this.intervalsCachingChunkDuration,
              this.intervalsCachingChunkUnit,
            ),
        );
      } else {
        this.ensureCacheFilledForInterval(
          startDate ||
            DateHelper.add(
              cacheCursorDate,
              -this.intervalsCachingChunkDuration,
              this.intervalsCachingChunkUnit,
            ),
          cacheCursorDate,
        );
      }
      let interval = intervalCache.getIntervalOf(
        cursorDate,
        isForward ? EdgeInclusion.Left : EdgeInclusion.Right,
      );
      while (interval) {
        const intervalStartDate = interval.startDate;
        const intervalEndDate = interval.endDate;
        if (
          (isForward && endDateN && intervalStartDate.getTime() >= endDateN) ||
          (!isForward && startDateN && intervalEndDate.getTime() <= startDateN)
        ) {
          return CalendarIteratorResult.FullRangeIterated;
        }
        if (
          (isForward && intervalStartDate.getTime() - rangeStart >= maxRange) ||
          (!isForward && rangeStart - intervalEndDate.getTime() >= maxRange)
        ) {
          return CalendarIteratorResult.MaxRangeReached;
        }
        if (
          (isForward &&
            intervalStartDate.getTime() >= this.cacheFilledEndDate.getTime()) ||
          (!isForward &&
            intervalEndDate.getTime() <= this.cacheFilledStartDate.getTime())
        ) {
          break;
        }
        cursorDate = isForward ? intervalEndDate : intervalStartDate;
        const countFrom =
          startDateN && intervalStartDate.getTime() < startDateN
            ? startDate
            : intervalStartDate;
        const countTill =
          endDateN && intervalEndDate.getTime() > endDateN
            ? endDate
            : intervalEndDate;
        if (
          func.call(scope, countFrom, countTill, interval.cacheInterval) ===
          false
        ) {
          return CalendarIteratorResult.StoppedByIterator;
        }
        interval = isForward
          ? intervalCache.getNextInterval(interval)
          : intervalCache.getPrevInterval(interval);
      }
      if (
        (isForward && cursorDate.getTime() === MAX_DATE.getTime()) ||
        (!isForward && cursorDate.getTime() === MIN_DATE.getTime())
      ) {
        return CalendarIteratorResult.FullRangeIterated;
      }
      cacheCursorDate = isForward
        ? this.cacheFilledEndDate
        : this.cacheFilledStartDate;
    }
    return CalendarIteratorResult.MaxCacheExtendCyclesReached;
  }
};

// ../Engine/lib/Engine/util/StripDuplicates.js
var stripDuplicates = (array) => Array.from(new Set(array));

// ../Engine/lib/Engine/calendar/CalendarCacheInterval.js
var CalendarCacheInterval = class _CalendarCacheInterval {
  constructor(config) {
    this.intervals = [];
    config && Object.assign(this, config);
    if (!this.calendar)
      throw new Error("Required attribute `calendar` is missing");
  }
  includeInterval(interval) {
    if (this.intervals.indexOf(interval) == -1) {
      const copy = this.intervals.slice();
      copy.push(interval);
      return new _CalendarCacheInterval({
        intervals: copy,
        calendar: this.calendar,
      });
    } else return this;
  }
  combineWith(interval) {
    return new _CalendarCacheInterval({
      intervals: this.intervals.concat(interval.intervals),
      calendar: this.calendar,
    });
  }
  /**
   * Returns the working status of this intervals set. It is determined as a working status
   * of the most prioritized interval (intervals are prioritized from child to parent)
   */
  getIsWorking() {
    if (this.isWorking != null) return this.isWorking;
    const intervals = (this.intervals = this.normalizeIntervals(
      this.intervals,
    ));
    return (this.isWorking = intervals[0].isWorking);
  }
  normalizeIntervals(intervals) {
    const filtered = stripDuplicates(intervals);
    filtered.sort(
      (interval1, interval2) =>
        interval2.getPriorityField() - interval1.getPriorityField(),
    );
    return filtered;
  }
};

// ../Engine/lib/Engine/util/BinarySearch.js
var binarySearch = (value, array, comparator = (a, b) => a - b) => {
  let left = 0;
  let right = array.length;
  while (left < right) {
    const mid = ((left + right) / 2) | 0;
    const compare = comparator(value, array[mid]);
    if (compare === 0) return { found: true, index: mid };
    else if (compare < 0) right = mid;
    else left = mid + 1;
  }
  return { found: false, index: right };
};

// ../Engine/lib/Engine/calendar/SortedMap.js
var IndexPosition;
(function (IndexPosition2) {
  IndexPosition2[(IndexPosition2["Exact"] = 0)] = "Exact";
  IndexPosition2[(IndexPosition2["Next"] = 1)] = "Next";
})(IndexPosition || (IndexPosition = {}));
var SortedMap = class {
  constructor(comparator) {
    this.keys = [];
    this.values = [];
    this.comparator = comparator || ((a, b) => a - b);
  }
  set(key, value) {
    const search = binarySearch(key, this.keys, this.comparator);
    if (search.found) {
      this.values[search.index] = value;
    } else {
      this.keys.splice(search.index, 0, key);
      this.values.splice(search.index, 0, value);
    }
    return search.index;
  }
  // you need to know what you are doing when using this method
  insertAt(index, key, value) {
    this.keys.splice(index, 0, key);
    this.values.splice(index, 0, value);
  }
  setValueAt(index, value) {
    this.values[index] = value;
  }
  get(key) {
    const search = binarySearch(key, this.keys, this.comparator);
    return search.found ? this.values[search.index] : void 0;
  }
  getEntryAt(index) {
    return index < this.keys.length
      ? { key: this.keys[index], value: this.values[index] }
      : void 0;
  }
  getKeyAt(index) {
    return this.keys[index];
  }
  getValueAt(index) {
    return this.values[index];
  }
  delete(key) {
    const search = binarySearch(key, this.keys, this.comparator);
    if (search.found) this.deleteAt(search.index);
  }
  size() {
    return this.keys.length;
  }
  deleteAt(index) {
    this.keys.splice(index, 1);
    this.values.splice(index, 1);
  }
  indexOfKey(key) {
    const search = binarySearch(key, this.keys, this.comparator);
    return {
      found: search.found ? IndexPosition.Exact : IndexPosition.Next,
      index: search.index,
    };
  }
  map(func) {
    const keys = this.keys;
    const values = this.values;
    const result = [];
    for (let i = 0; i < keys.length; i++)
      result.push(func(values[i], keys[i], i));
    return result;
  }
  getAllEntries() {
    return this.map((value, key) => {
      return { value, key };
    });
  }
  clear() {
    this.keys.length = 0;
    this.values.length = 0;
  }
};

// ../Engine/lib/Engine/calendar/IntervalCache.js
var IntervalCache = class {
  constructor(config) {
    this.points = new SortedMap((a, b) => a.getTime() - b.getTime());
    this.leftInfinityKey = MIN_DATE;
    this.rightInfinityKey = MAX_DATE;
    Object.assign(this, config);
    if (this.emptyInterval === void 0 || !this.combineIntervalsFn)
      throw new Error("All of `emptyPoint`, `combineIntervalsFn` are required");
    this.points.set(this.leftInfinityKey, this.emptyInterval);
  }
  size() {
    return this.points.size();
  }
  indexOf(date) {
    return this.points.indexOfKey(date);
  }
  getDateAt(index) {
    return this.points.getKeyAt(index);
  }
  getPointAt(index) {
    return this.points.getValueAt(index);
  }
  getIntervalOf(date, edgeInclusion = EdgeInclusion.Left) {
    let { found, index } = this.indexOf(date);
    let startDateIndex;
    if (edgeInclusion === EdgeInclusion.Left) {
      startDateIndex = found === IndexPosition.Exact ? index : index - 1;
    } else {
      startDateIndex = index - 1;
    }
    return this.getIntervalWithStartDateIndex(startDateIndex);
  }
  getPrevInterval(interval) {
    if (interval.startDateIndex === 0) return null;
    return this.getIntervalWithStartDateIndex(interval.startDateIndex - 1);
  }
  getNextInterval(interval) {
    if (interval.startDateIndex >= this.size() - 1) return null;
    return this.getIntervalWithStartDateIndex(interval.startDateIndex + 1);
  }
  getIntervalWithStartDateIndex(startDateIndex) {
    return {
      startDateIndex,
      startDate: this.getDateAt(startDateIndex),
      endDate:
        startDateIndex + 1 < this.size()
          ? this.getDateAt(startDateIndex + 1)
          : this.rightInfinityKey,
      cacheInterval: this.getPointAt(startDateIndex),
    };
  }
  addInterval(startDate, endDate, extendInterval) {
    const points = this.points;
    const { found, index } = points.indexOfKey(startDate);
    let curIndex;
    let lastUpdatedPoint;
    if (found == IndexPosition.Exact) {
      const inclusion = extendInterval(
        (lastUpdatedPoint = points.getValueAt(index)),
      );
      points.setValueAt(index, inclusion);
      curIndex = index + 1;
    } else {
      const inclusion = extendInterval(
        (lastUpdatedPoint = points.getValueAt(index - 1)),
      );
      points.insertAt(index, startDate, inclusion);
      curIndex = index + 1;
    }
    while (curIndex < points.size()) {
      const curDate = points.getKeyAt(curIndex);
      if (curDate.getTime() >= endDate.getTime()) break;
      const inclusion = extendInterval(
        (lastUpdatedPoint = points.getValueAt(curIndex)),
      );
      points.setValueAt(curIndex, inclusion);
      curIndex++;
    }
    if (curIndex === points.size()) {
      points.insertAt(points.size(), endDate, this.emptyInterval);
    } else {
      const curDate = points.getKeyAt(curIndex);
      if (curDate.getTime() === endDate.getTime()) {
      } else {
        points.insertAt(curIndex, endDate, lastUpdatedPoint);
      }
    }
  }
  includeWrappingRange(intervalCache, startDate, endDate) {
    let interval = intervalCache.getIntervalOf(startDate);
    while (interval) {
      this.addInterval(
        interval.startDate,
        interval.endDate,
        (existingInterval) =>
          this.combineIntervalsFn(existingInterval, interval.cacheInterval),
      );
      if (interval.endDate.getTime() > endDate.getTime()) break;
      interval = intervalCache.getNextInterval(interval);
    }
  }
  getSummary() {
    return this.points.map((label, date) => {
      return { label, date };
    });
  }
  clear() {
    this.points.clear();
    this.points.set(this.leftInfinityKey, this.emptyInterval);
  }
};

// ../Engine/lib/Engine/calendar/CalendarCacheSingle.js
var CalendarCacheSingle = class extends CalendarCache {
  constructor(config) {
    super(config);
    this.staticIntervalsCached = false;
    if (!this.unspecifiedTimeInterval)
      throw new Error(
        "Required attribute `unspecifiedTimeInterval` is missing",
      );
    this.intervalCache = new IntervalCache({
      emptyInterval: new CalendarCacheInterval({
        intervals: [this.unspecifiedTimeInterval],
        calendar: this.calendar,
      }),
      combineIntervalsFn: (interval1, interval2) => {
        return interval1.combineWith(interval2);
      },
    });
  }
  fillCache(startDate, endDate) {
    var _a4;
    if (!this.staticIntervalsCached) {
      this.cacheStaticIntervals();
      this.staticIntervalsCached = true;
    }
    if (this.parentCache)
      this.includeWrappingRangeFrom(this.parentCache, startDate, endDate);
    const startDateN = startDate.getTime();
    const endDateN = endDate.getTime();
    const timeZone = this.calendar.ignoreTimeZone
      ? null
      : (_a4 = this.calendar.project) == null
        ? void 0
        : _a4.timeZone;
    if (startDateN > endDateN) throw new Error("Invalid cache fill interval");
    const NEVER = later_default.NEVER;
    this.forEachRecurrentInterval((interval) => {
      const startSchedule = interval.getStartDateSchedule();
      const endSchedule = interval.getEndDateSchedule();
      let wrappingStartDate = startSchedule.prev(1, startDate);
      let wrappingEndDate;
      if (endSchedule === "EOD") {
        const nextEndDate = startSchedule.next(1, endDate);
        if (nextEndDate !== NEVER) {
          wrappingEndDate = DateHelper.getStartOfNextDay(nextEndDate, true);
        } else {
          wrappingEndDate = NEVER;
        }
      } else {
        wrappingEndDate = endSchedule.next(1, endDate);
      }
      if (
        wrappingStartDate !== NEVER &&
        wrappingStartDate.getTime() === startDateN
      ) {
        const wrappingStartDates = startSchedule.prev(2, startDate);
        if (wrappingStartDates !== NEVER && wrappingStartDates.length === 2)
          wrappingStartDate = wrappingStartDates[1];
      }
      if (wrappingEndDate !== NEVER && wrappingEndDate.getTime() === endDateN) {
        const wrappingEndDates = endSchedule.next(2, endDate);
        if (wrappingEndDates !== NEVER && wrappingEndDates.length === 2)
          wrappingEndDate = wrappingEndDates[1];
      }
      const startDates = startSchedule.next(
        Infinity,
        wrappingStartDate !== NEVER ? wrappingStartDate : startDate,
        wrappingEndDate !== NEVER
          ? new Date(wrappingEndDate.getTime() - 1)
          : endDate,
      );
      if (startDates === NEVER) return;
      const endDates =
        endSchedule === "EOD"
          ? startDates.map((date) => DateHelper.getStartOfNextDay(date, true))
          : endSchedule.next(
              Infinity,
              new Date(startDates[0].getTime() + 1),
              wrappingEndDate !== NEVER ? wrappingEndDate : endDate,
            );
      if (endDates === NEVER) return;
      if (endDates.length > startDates.length) {
        endDates.length = startDates.length;
      } else if (endDates.length < startDates.length) {
        startDates.length = endDates.length;
      }
      startDates.forEach((startDate2, index) => {
        let recStartDate = startDate2;
        let recEndDate = endDates[index];
        if (timeZone != null) {
          recStartDate = TimeZoneHelper.toTimeZone(recStartDate, timeZone);
          recEndDate = TimeZoneHelper.toTimeZone(recEndDate, timeZone);
        }
        this.intervalCache.addInterval(
          recStartDate,
          recEndDate,
          (existingCacheInterval) =>
            existingCacheInterval.includeInterval(interval),
        );
      });
    });
  }
  clear() {
    this.staticIntervalsCached = false;
    super.clear();
  }
  cacheStaticIntervals() {
    this.forEachStaticInterval((interval) => {
      var _a4;
      const timeZone =
        (_a4 = this.calendar.project) == null ? void 0 : _a4.timeZone;
      let { startDate, endDate } = interval;
      if (timeZone != null) {
        startDate = TimeZoneHelper.toTimeZone(startDate, timeZone);
        endDate = TimeZoneHelper.toTimeZone(endDate, timeZone);
      }
      this.intervalCache.addInterval(
        startDate,
        endDate,
        (existingCacheInterval) =>
          existingCacheInterval.includeInterval(interval),
      );
    });
  }
  forEachStaticInterval(func) {
    this.intervalStore.forEach((interval) => {
      if (interval.isStatic()) func(interval);
    });
  }
  forEachRecurrentInterval(func) {
    this.intervalStore.forEach((interval) => {
      if (interval.isRecurrent()) func(interval);
    });
  }
};

// ../Engine/lib/Engine/calendar/UnspecifiedTimeIntervalModel.js
var UnspecifiedTimeIntervalModel = class extends Mixin(
  [CalendarIntervalMixin],
  (base) => {
    const superProto = base.prototype;
    class UnspecifiedTimeIntervalModel2 extends base {
      getCalendar() {
        return this.calendar;
      }
      // NOTE: See parent class implementation for further comments
      getPriorityField() {
        if (this.priorityField != null) return this.priorityField;
        return (this.priorityField = this.getCalendar().getDepth());
      }
    }
    return UnspecifiedTimeIntervalModel2;
  },
) {};

// ../Engine/lib/Engine/quark/model/AbstractCalendarMixin.js
var AbstractCalendarMixin = class extends Mixin(
  [AbstractPartOfProjectModelMixin],
  (base) => {
    const superProto = base.prototype;
    class CalendarMixin extends base {
      constructor() {
        super(...arguments);
        this.version = 1;
      }
      static get fields() {
        return [
          { name: "version", type: "number" },
          "name",
          {
            name: "unspecifiedTimeIsWorking",
            type: "boolean",
            defaultValue: true,
          },
          { name: "intervals", type: "store", subStore: true },
          "cls",
          "iconCls",
        ];
      }
      get intervalStoreClass() {
        return CalendarIntervalStore;
      }
      get intervalStore() {
        return this.meta.intervalsStore;
      }
      // Not a typo, name is generated from the fields name = intervals
      initIntervalsStore(config) {
        config.storeClass = this.intervalStoreClass;
        config.modelClass =
          this.getDefaultConfiguration().calendarIntervalModelClass ||
          this.intervalStoreClass.defaultConfig.modelClass;
        config.calendar = this;
      }
      // this method is called when the new value for the `intervals` field of this model is assigned
      // the type of the `intervals` field is "store" that's why this magic
      processIntervalsStoreData(intervals) {
        this.bumpVersion();
      }
      isDefault() {
        const project = this.getProject();
        if (project) {
          return this === project.defaultCalendar;
        }
        return false;
      }
      getDepth() {
        return this.childLevel + 1;
      }
      /**
       * The core iterator method of the calendar.
       *
       * @param options The options for iterator. Should contain at least one of the `startDate`/`endDate` properties
       * which indicates what timespan to examine for availability intervals. If one of boundaries is not provided
       * iterator function should return `false` at some point, to avoid infinite loops.
       *
       * Another recognized option is `isForward`, which indicates the direction in which to iterate through the timespan.
       *
       * @param func The iterator function to call. It will be called for every distinct set of availability intervals, found
       * in the given timespan. All the intervals, which are "active" for current interval are collected in the 3rd argument
       * for this function - [[CalendarCacheInterval|calendarCacheInterval]]. If iterator returns `false` (checked with `===`)
       * the iteration stops.
       *
       * @param scope The scope (`this` value) to execute the iterator in.
       */
      forEachAvailabilityInterval(options, func, scope) {
        var _a4, _b;
        const maxRange =
          (_b = options.maxRange) != null
            ? _b
            : (_a4 = this.getProject()) == null
              ? void 0
              : _a4.maxCalendarRange;
        if (maxRange) {
          options = { ...options, maxRange };
        }
        return this.calendarCache.forEachAvailabilityInterval(
          options,
          func,
          scope,
        );
      }
      /**
       * This method starts at the given `date` and moves forward or backward in time, depending on `isForward`.
       * It stops moving as soon as it accumulates the `durationMs` milliseconds of working time and returns the date
       * at which it has stopped and remaining duration - the [[AccumulateWorkingTimeResult]] object.
       *
       * Normally, the remaining duration will be 0, indicating the full `durationMs` has been accumulated.
       * However, sometimes, calendar might not be able to accumulate enough working time due to various reasons,
       * like if it does not contain enough working time - this case will be indicated with remaining duration bigger than 0.
       *
       * @param date
       * @param durationMs
       * @param isForward
       */
      accumulateWorkingTime(date, durationMs, isForward) {
        var _a4, _b, _c;
        if (durationMs === 0)
          return { finalDate: new Date(date), remainingDurationInMs: 0 };
        if (isNaN(durationMs)) throw new Error("Invalid duration");
        let finalDate = date;
        const adjustDurationToDST =
          (_c =
            (_b =
              (_a4 = this.getProject()) == null
                ? void 0
                : _a4.adjustDurationToDST) != null
              ? _b
              : this.adjustDurationToDST) != null
            ? _c
            : false;
        this.forEachAvailabilityInterval(
          isForward
            ? { startDate: date, isForward: true }
            : { endDate: date, isForward: false },
          (intervalStartDate, intervalEndDate, calendarCacheInterval) => {
            let result = true;
            if (calendarCacheInterval.getIsWorking()) {
              let diff =
                intervalEndDate.getTime() - intervalStartDate.getTime();
              if (durationMs <= diff) {
                if (adjustDurationToDST) {
                  const dstDiff = isForward
                    ? intervalStartDate.getTimezoneOffset() -
                      new Date(
                        intervalStartDate.getTime() + durationMs,
                      ).getTimezoneOffset()
                    : new Date(
                        intervalEndDate.getTime() - durationMs,
                      ).getTimezoneOffset() -
                      intervalEndDate.getTimezoneOffset();
                  durationMs -= dstDiff * 60 * 1e3;
                }
                finalDate = isForward
                  ? new Date(intervalStartDate.getTime() + durationMs)
                  : new Date(intervalEndDate.getTime() - durationMs);
                durationMs = 0;
                result = false;
              } else {
                if (adjustDurationToDST) {
                  const dstDiff =
                    intervalStartDate.getTimezoneOffset() -
                    intervalEndDate.getTimezoneOffset();
                  diff += dstDiff * 60 * 1e3;
                }
                finalDate = isForward ? intervalEndDate : intervalStartDate;
                durationMs -= diff;
              }
            }
            return result;
          },
        );
        return {
          finalDate: new Date(finalDate),
          remainingDurationInMs: durationMs,
        };
      }
      /**
       * Calculate the working time duration between the 2 dates, in milliseconds.
       *
       * @param {Date} startDate
       * @param {Date} endDate
       * @param {Boolean} [allowNegative] Method ignores negative values by default, returning 0. Set to true to get
       * negative duration.
       */
      calculateDurationMs(startDate, endDate, allowNegative = false) {
        var _a4, _b, _c;
        let duration = 0;
        const multiplier =
          startDate.getTime() <= endDate.getTime() || !allowNegative ? 1 : -1;
        if (multiplier < 0) {
          [startDate, endDate] = [endDate, startDate];
        }
        const adjustDurationToDST =
          (_c =
            (_b =
              (_a4 = this.getProject()) == null
                ? void 0
                : _a4.adjustDurationToDST) != null
              ? _b
              : this.adjustDurationToDST) != null
            ? _c
            : false;
        this.forEachAvailabilityInterval(
          { startDate, endDate },
          (intervalStartDate, intervalEndDate, calendarCacheInterval) => {
            if (calendarCacheInterval.getIsWorking()) {
              duration +=
                intervalEndDate.getTime() - intervalStartDate.getTime();
              if (adjustDurationToDST) {
                const dstDiff =
                  intervalStartDate.getTimezoneOffset() -
                  intervalEndDate.getTimezoneOffset();
                duration += dstDiff * 60 * 1e3;
              }
            }
          },
        );
        return duration * multiplier;
      }
      /**
       * Calculate the end date of the time interval which starts at `startDate` and has `durationMs` working time duration
       * (in milliseconds).
       *
       * @param startDate
       * @param durationMs
       */
      calculateEndDate(startDate, durationMs) {
        const isForward = durationMs >= 0;
        const res = this.accumulateWorkingTime(
          startDate,
          Math.abs(durationMs),
          isForward,
        );
        return res.remainingDurationInMs === 0 ? res.finalDate : null;
      }
      /**
       * Calculate the start date of the time interval which ends at `endDate` and has `durationMs` working time duration
       * (in milliseconds).
       *
       * @param endDate
       * @param durationMs
       */
      calculateStartDate(endDate, durationMs) {
        const isForward = durationMs <= 0;
        const res = this.accumulateWorkingTime(
          endDate,
          Math.abs(durationMs),
          isForward,
        );
        return res.remainingDurationInMs === 0 ? res.finalDate : null;
      }
      /**
       * Returns the earliest point at which a working period of time starts, following the given date.
       * Can be the date itself, if it comes on the working time.
       *
       * @param date The date after which to skip the non-working time.
       * @param isForward Whether the "following" means forward in time or backward.
       */
      skipNonWorkingTime(date, isForward = true) {
        let workingDate;
        const res = this.forEachAvailabilityInterval(
          isForward
            ? { startDate: date, isForward: true }
            : { endDate: date, isForward: false },
          (intervalStartDate, intervalEndDate, calendarCacheInterval) => {
            if (calendarCacheInterval.getIsWorking()) {
              workingDate = isForward ? intervalStartDate : intervalEndDate;
              return false;
            }
          },
        );
        if (
          res === CalendarIteratorResult.MaxRangeReached ||
          res === CalendarIteratorResult.FullRangeIterated
        )
          return "empty_calendar";
        return workingDate ? new Date(workingDate) : new Date(date);
      }
      /**
       * This method adds a single [[CalendarIntervalMixin]] to the internal collection of the calendar
       */
      addInterval(interval) {
        return this.addIntervals([interval]);
      }
      /**
       * This method adds an array of [[CalendarIntervalMixin]] to the internal collection of the calendar
       */
      addIntervals(intervals) {
        this.bumpVersion();
        return this.intervalStore.add(intervals);
      }
      /**
       * This method removes a single [[CalendarIntervalMixin]] from the internal collection of the calendar
       */
      removeInterval(interval) {
        return this.removeIntervals([interval]);
      }
      /**
       * This method removes an array of [[CalendarIntervalMixin]] from the internal collection of the calendar
       */
      removeIntervals(intervals) {
        this.bumpVersion();
        return this.intervalStore.remove(intervals);
      }
      /**
       * This method removes all intervals from the internal collection of the calendar
       */
      clearIntervals(silent) {
        if (!silent) {
          this.bumpVersion();
        }
        return this.intervalStore.removeAll(silent);
      }
      bumpVersion() {
        this.clearCache();
        this.version++;
      }
      get calendarCache() {
        if (this.$calendarCache !== void 0) return this.$calendarCache;
        const unspecifiedTimeInterval = new UnspecifiedTimeIntervalModel({
          isWorking: this.unspecifiedTimeIsWorking,
        });
        unspecifiedTimeInterval.calendar = this;
        return (this.$calendarCache = new CalendarCacheSingle({
          calendar: this,
          unspecifiedTimeInterval,
          intervalStore: this.intervalStore,
          parentCache:
            this.parent && !this.parent.isRoot
              ? this.parent.calendarCache
              : null,
        }));
      }
      clearCache() {
        this.$calendarCache && this.$calendarCache.clear();
        this.$calendarCache = void 0;
      }
      resetPriorityOfAllIntervals() {
        this.traverse((calendar) => {
          calendar.intervalStore.forEach((interval) =>
            interval.resetPriority(),
          );
        });
      }
      insertChild(child, before, silent) {
        let res = superProto.insertChild.call(this, ...arguments);
        if (!Array.isArray(res)) {
          res = [res];
        }
        res.forEach((r) => {
          r.bumpVersion();
          r.resetPriorityOfAllIntervals();
        });
        return res;
      }
      joinProject() {
        superProto.joinProject.call(this);
        this.intervalStore.setProject(this.getProject());
      }
      leaveProject() {
        superProto.leaveProject.call(this);
        this.intervalStore.setProject(null);
        this.clearCache();
      }
      doDestroy() {
        this.leaveProject();
        this.intervalStore.destroy();
        super.doDestroy();
      }
      isDayHoliday(day2) {
        const startDate = DateHelper.clearTime(day2),
          endDate = DateHelper.getNext(day2, TimeUnit.Day);
        let hasWorkingTime = false;
        this.forEachAvailabilityInterval(
          { startDate, endDate, isForward: true },
          (_intervalStartDate, _intervalEndDate, calendarCacheInterval) => {
            hasWorkingTime = calendarCacheInterval.getIsWorking();
            return !hasWorkingTime;
          },
        );
        return !hasWorkingTime;
      }
      getDailyHolidaysRanges(startDate, endDate) {
        const result = [];
        startDate = DateHelper.clearTime(startDate);
        while (startDate < endDate) {
          if (this.isDayHoliday(startDate)) {
            result.push({
              startDate,
              endDate: DateHelper.getStartOfNextDay(startDate, true, true),
            });
          }
          startDate = DateHelper.getNext(startDate, TimeUnit.Day);
        }
        return result;
      }
      /**
       * Returns working time ranges between the provided dates.
       * @param {Date} startDate Start of the period to get ranges from.
       * @param {Date} endDate End of the period to get ranges from.
       */
      getWorkingTimeRanges(startDate, endDate, maxRange) {
        const result = [];
        this.forEachAvailabilityInterval(
          { startDate, endDate, isForward: true, maxRange },
          (intervalStartDate, intervalEndDate, calendarCacheInterval) => {
            if (calendarCacheInterval.getIsWorking()) {
              const entry = calendarCacheInterval.intervals[0];
              result.push({
                name: entry.name,
                startDate: intervalStartDate,
                endDate: intervalEndDate,
              });
            }
          },
        );
        return result;
      }
      /**
       * Returns non-working time ranges between the provided dates.
       * @param {Date} startDate Start of the period to get ranges from.
       * @param {Date} endDate End of the period to get ranges from.
       */
      getNonWorkingTimeRanges(startDate, endDate, maxRange) {
        const result = [];
        this.forEachAvailabilityInterval(
          { startDate, endDate, isForward: true, maxRange },
          (intervalStartDate, intervalEndDate, calendarCacheInterval) => {
            if (!calendarCacheInterval.getIsWorking()) {
              const entry = calendarCacheInterval.intervals[0];
              result.push({
                name: entry.name,
                iconCls: entry.iconCls,
                cls: entry.cls,
                startDate: intervalStartDate,
                endDate: intervalEndDate,
              });
            }
          },
        );
        return result;
      }
      /**
       * Checks if there is a working time interval in the provided time range (or when just startDate is provided,
       * checks if the date is contained inside a working time interval in this calendar)
       * @param startDate
       * @param [endDate]
       * @param [fullyContained] Pass true to check if the range is fully covered by a single continuous working time block
       */
      isWorkingTime(startDate, endDate, fullyContained) {
        if (fullyContained) {
          let found;
          const res = this.forEachAvailabilityInterval(
            { startDate, endDate, isForward: true },
            (intervalStartDate, intervalEndDate, calendarCacheInterval) => {
              if (
                calendarCacheInterval.getIsWorking() &&
                intervalStartDate <= startDate &&
                intervalEndDate >= endDate
              ) {
                found = true;
                return false;
              }
            },
          );
          if (
            res === CalendarIteratorResult.MaxRangeReached ||
            res === CalendarIteratorResult.FullRangeIterated
          )
            return false;
          return found;
        } else {
          const workingTimeStart = this.skipNonWorkingTime(startDate);
          return workingTimeStart && workingTimeStart !== "empty_calendar"
            ? endDate
              ? workingTimeStart < endDate
              : workingTimeStart.getTime() === startDate.getTime()
            : false;
        }
      }
    }
    return CalendarMixin;
  },
) {};

// ../Engine/lib/Engine/quark/model/scheduler_core/CoreCalendarMixin.js
var CoreCalendarMixin = class extends Mixin(
  [AbstractCalendarMixin, CorePartOfProjectModelMixin],
  (base) => {
    const superProto = base.prototype;
    class CoreCalendarMixin2 extends base {}
    return CoreCalendarMixin2;
  },
) {};

// ../Engine/lib/Engine/quark/store/AbstractCalendarManagerStoreMixin.js
var AbstractCalendarManagerStoreMixin = class extends Mixin(
  [AbstractPartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class AbstractCalendarManagerStoreMixin2 extends base {
      // special handling to destroy calendar models as part of destroying this store
      doDestroy() {
        var _a4;
        const records = [];
        if (!((_a4 = this.rootNode) == null ? void 0 : _a4.isDestroyed)) {
          this.traverse((record) => records.push(record));
        }
        super.doDestroy();
        records.forEach((record) => record.destroy());
      }
    }
    return AbstractCalendarManagerStoreMixin2;
  },
) {};

// ../Engine/lib/Engine/quark/store/CoreCalendarManagerStoreMixin.js
var CoreCalendarManagerStoreMixin = class extends Mixin(
  [AbstractCalendarManagerStoreMixin, CorePartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class CoreCalendarManagerStoreMixin2 extends base {
      static get defaultConfig() {
        return {
          tree: true,
          modelClass: CoreCalendarMixin,
        };
      }
    }
    return CoreCalendarManagerStoreMixin2;
  },
) {};

// ../Engine/lib/Engine/quark/model/AbstractProjectMixin.js
var EventsWrapper = class extends Mixin([], Events_default) {};
var DelayableWrapper = class extends Mixin([], Delayable_default) {};
var AbstractProjectMixin = class extends Mixin(
  [EventsWrapper, DelayableWrapper, Model],
  (base) => {
    const superProto = base.prototype;
    class AbstractProjectMixin2 extends base {
      constructor() {
        super(...arguments);
        this.isRestoringData = false;
      }
