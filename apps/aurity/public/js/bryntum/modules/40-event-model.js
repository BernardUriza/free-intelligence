    return SchedulerCoreEvent2;
  },
) {};

// ../Scheduler/lib/Scheduler/model/EventModel.js
var EngineMixin3 = SchedulerCoreEvent;
var EventModel = class extends EngineMixin3.derive(TimeSpan).mixin(
  RecurringTimeSpan_default,
  PartOfProject_default,
  EventModelMixin_default,
) {
  static get $name() {
    return "EventModel";
  }
};
EventModel.exposeProperties();
EventModel._$name = "EventModel";

// ../Engine/lib/Engine/quark/store/AbstractEventStoreMixin.js
var dataAddRemoveActions3 = {
  splice: 1,
  clear: 1,
};
var AbstractEventStoreMixin = class extends Mixin(
  [AbstractPartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class AbstractEventStoreMixin2 extends base {
      constructor() {
        super(...arguments);
        this.assignmentsForRemoval = /* @__PURE__ */ new Set();
        this.dependenciesForRemoval = /* @__PURE__ */ new Set();
      }
      // we need `onDataChange` for `syncDataOnLoad` option to work
      onDataChange(event) {
        var _a4;
        const isAddRemove = dataAddRemoveActions3[event.action];
        super.onDataChange(event);
        if (
          isAddRemove &&
          ((_a4 = event.removed) == null ? void 0 : _a4.length)
        )
          this.afterEventRemoval();
      }
      // it seems `onDataChange` is not triggered for `remove` with `silent` flag
      remove(records, silent) {
        const res = superProto.remove.call(this, records, silent);
        this.afterEventRemoval();
        return res;
      }
      // it seems `onDataChange` is not triggered for `TreeStore#removeAll()`
      removeAll(silent) {
        const res = superProto.removeAll.call(this, silent);
        this.afterEventRemoval();
        return res;
      }
      onNodeRemoveChild(parent, children, index, flags) {
        const removed = superProto.onNodeRemoveChild.call(this, ...arguments);
        this.afterEventRemoval();
        return removed;
      }
      afterEventRemoval() {
        const { assignmentsForRemoval, dependenciesForRemoval } = this;
        if (!assignmentsForRemoval) return;
        const assignmentStore = this.getAssignmentStore();
        if (
          assignmentStore &&
          !assignmentStore.allAssignmentsForRemoval &&
          assignmentsForRemoval.size
        ) {
          const toRemove = [...assignmentsForRemoval].filter(
            (assignment) =>
              !assignmentStore.assignmentsForRemoval.has(assignment),
          );
          toRemove.length > 0 && assignmentStore.remove(toRemove);
        }
        assignmentsForRemoval.clear();
        const dependencyStore = this.getDependencyStore();
        if (
          dependencyStore &&
          !dependencyStore.allDependenciesForRemoval &&
          dependenciesForRemoval.size
        ) {
          const toRemove = [...dependenciesForRemoval].filter(
            (dependency) =>
              !dependencyStore.dependenciesForRemoval.has(dependency),
          );
          toRemove.length > 0 && dependencyStore.remove(toRemove);
        }
        dependenciesForRemoval.clear();
      }
      processRecord(eventRecord, isDataset = false) {
        var _a4;
        if (
          !((_a4 = this.project) == null ? void 0 : _a4.isRepopulatingStores)
        ) {
          const existingRecord = this.getById(eventRecord.id);
          const isReplacing = existingRecord && existingRecord !== eventRecord;
          if (isReplacing && existingRecord.assigned) {
            for (const assignment of existingRecord.assigned) {
              assignment.event = eventRecord;
            }
          }
        }
        return eventRecord;
      }
    }
    return AbstractEventStoreMixin2;
  },
) {};

// ../Engine/lib/Engine/quark/store/CoreEventStoreMixin.js
var CoreEventStoreMixin = class extends Mixin(
  [AbstractEventStoreMixin, CorePartOfProjectStoreMixin],
  (base) => {
    const superProto = base.prototype;
    class CoreEventStoreMixin2 extends base {
      static get defaultConfig() {
        return {
          modelClass: SchedulerCoreEvent,
        };
      }
      joinProject() {
        var _a4;
        (_a4 = this.assignmentStore) == null
          ? void 0
          : _a4.linkAssignments(this, "event");
      }
      afterLoadData() {
        var _a4;
        this.afterEventRemoval();
        (_a4 = this.assignmentStore) == null
          ? void 0
          : _a4.linkAssignments(this, "event");
      }
    }
    return CoreEventStoreMixin2;
  },
) {};

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
