    return null;
  }
  //endregion
  //#region Salesforce hooks
  getMouseMoveEventTarget(event) {
    return event.target;
  }
  //#endregion
};
EventDrag._$name = "EventDrag";
GridFeatureManager.registerFeature(EventDrag, true, "Scheduler");
GridFeatureManager.registerFeature(EventDrag, false, "ResourceHistogram");

// ../Scheduler/lib/Scheduler/feature/EventDragCreate.js
var EventDragCreate = class extends DragCreateBase {
  //endregion
  //region Events
  /**
   * Fires on the owning Scheduler after the new event has been created.
   * @event dragCreateEnd
   * @on-owner
   * @param {Scheduler.view.Scheduler} source
   * @param {Scheduler.model.EventModel} eventRecord The new `EventModel` record.
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource for the row in which the event is being
   * created.
   * @param {MouseEvent} event The ending mouseup event.
   * @param {HTMLElement} eventElement The DOM element representing the newly created event un the UI.
   */
  /**
   * Fires on the owning Scheduler at the beginning of the drag gesture. Returning `false` from a listener prevents
   * the drag create operation from starting.
   *
   * ```javascript
   * const scheduler = new Scheduler({
   *     listeners : {
   *         beforeDragCreate({ date }) {
   *             // Prevent drag creating events in the past
   *             return date >= Date.now();
   *         }
   *     }
   * });
   * ```
   *
   * @event beforeDragCreate
   * @on-owner
   * @preventable
   * @param {Scheduler.view.Scheduler} source
   * @param {Scheduler.model.ResourceModel} resourceRecord
   * @param {Date} date The datetime associated with the drag start point.
   */
  /**
   * Fires on the owning Scheduler after the drag start has created a new Event record.
   * @event dragCreateStart
   * @on-owner
   * @param {Scheduler.view.Scheduler} source
   * @param {Scheduler.model.EventModel} eventRecord The event record being created
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource record
   * @param {HTMLElement} eventElement The element representing the new event.
   */
  /**
   * Fires on the owning Scheduler to allow implementer to prevent immediate finalization by setting
   * `data.context.async = true` in the listener, to show a confirmation popup etc
   * ```javascript
   *  scheduler.on('beforedragcreatefinalize', ({context}) => {
   *      context.async = true;
   *      setTimeout(() => {
   *          // async code don't forget to call finalize
   *          context.finalize();
   *      }, 1000);
   *  })
   * ```
   * @event beforeDragCreateFinalize
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.EventModel} eventRecord The event record being created
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource record
   * @param {HTMLElement} eventElement The element representing the new Event record
   * @param {Object} context
   * @param {Boolean} context.async Set true to handle drag create asynchronously (e.g. to wait for user
   * confirmation)
   * @param {Function} context.finalize Call this method to finalize drag create. This method accepts one
   * argument: pass true to update records, or false, to ignore changes
   */
  /**
   * Fires on the owning Scheduler at the end of the drag create gesture whether or not
   * a new event was created by the gesture.
   * @event afterDragCreate
   * @on-owner
   * @param {Scheduler.view.Scheduler} source
   * @param {Scheduler.model.EventModel} eventRecord The event record being created
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource record
   * @param {HTMLElement} eventElement The element representing the created event record
   */
  //endregion
  //region Init
  get scheduler() {
    return this.client;
  }
  get store() {
    return this.client.eventStore;
  }
  get project() {
    return this.client.project;
  }
  updateLockLayout(lock) {
    this.dragActiveCls = `b-dragcreating${lock ? " b-dragcreate-lock" : ""}`;
  }
  //endregion
  //region Scheduler specific implementation
  handleBeforeDragCreate(drag, eventRecord, event) {
    var _a4;
    const me = this,
      { scheduler, store } = me,
      { resourceRecord } = drag;
    if (
      me.disabled ||
      resourceRecord.readOnly ||
      !me.scheduler.resourceStore.isAvailable(resourceRecord)
    ) {
      return false;
    }
    if (scheduler.allowOverlap === false) {
      const isEventOverlapped = !store.isDateRangeAvailable(
        drag.mousedownDate,
        drag.mousedownDate,
        null,
        resourceRecord,
      );
      if (isEventOverlapped) {
        return false;
      }
    }
    // PATCHED by FI: Check global validation function if available
    // This allows our app to block drag-create in non-working hours
    const fiValidation = typeof window.__FI_VALIDATE_WORKING_TIME__ === 'function'
        ? window.__FI_VALIDATE_WORKING_TIME__(resourceRecord.id, drag.mousedownDate)
        : true,
      isWorkingTime2 =
        fiValidation && (
          !scheduler.isSchedulerPro ||
          eventRecord.ignoreResourceCalendar ||
          resourceRecord.isWorkingTime(drag.mousedownDate)
        ),
      result =
        isWorkingTime2 &&
        scheduler.trigger("beforeDragCreate", {
          resourceRecord,
          date: drag.mousedownDate,
          event,
        });
    me.dateConstraints =
      (_a4 = scheduler.getDateConstraints) == null
        ? void 0
        : _a4.call(scheduler, resourceRecord, eventRecord);
    return result;
  }
  dragStart(drag) {
    var _a4;
    const me = this,
      { client } = me,
      {
        eventStore,
        assignmentStore,
        enableEventAnimations,
        enableTransactionalFeatures,
      } = client,
      { resourceRecord } = drag,
      eventRecord = me.createEventRecord(drag),
      resourceRecords = [resourceRecord];
    eventRecord.set(
      "duration",
      DateHelper.diff(
        eventRecord.startDate,
        eventRecord.endDate,
        eventRecord.durationUnit,
        true,
      ),
    );
    eventRecord.isCreating = true;
    eventRecord.meta.isDragCreating = true;
    client.features.taskEdit && client.features.taskEdit.doCancel();
    if (me.handleBeforeDragCreate(drag, eventRecord, drag.event) === false) {
      return false;
    }
    me.captureStm(true);
    let assignmentRecords = [];
    if (resourceRecord) {
      if (eventStore.usesSingleAssignment || !enableTransactionalFeatures) {
        assignmentRecords = assignmentStore.assignEventToResource(
          eventRecord,
          resourceRecord,
        );
      } else {
        assignmentRecords = [
          assignmentStore.createRecord({
            event: eventRecord,
            resource: resourceRecord,
          }),
        ];
      }
    }
    if (
      client.trigger("beforeEventAdd", {
        eventRecord,
        resourceRecords,
        assignmentRecords,
      }) === false
    ) {
      if (eventStore.usesSingleAssignment || !enableTransactionalFeatures) {
        assignmentStore.remove(assignmentRecords);
      }
      return false;
    }
    if (me.lockLayout) {
      eventRecord.meta.excludeFromLayout = true;
    }
    (_a4 = client.onEventCreated) == null
      ? void 0
      : _a4.call(client, eventRecord);
    client.enableEventAnimations = false;
    eventStore
      .addAsync(eventRecord)
      .then(() => (client.enableEventAnimations = enableEventAnimations));
    if (!eventStore.usesSingleAssignment && enableTransactionalFeatures) {
      assignmentStore.add(assignmentRecords[0]);
    }
    client.isCreating = true;
    client.refreshRows();
    client.isCreating = false;
    drag.itemElement = drag.element =
      client.getElementFromEventRecord(eventRecord);
    if (!DomHelper.isInView(drag.itemElement)) {
      client.scrollable.scrollIntoView(drag.itemElement, {
        animate: true,
        edgeOffset: client.barMargin,
      });
    }
    return super.dragStart(drag);
  }
  checkValidity(context, event) {
    const me = this,
      { client } = me;
    context.resourceRecord = me.dragging.resourceRecord;
    return (
      (client.allowOverlap ||
        client.isDateRangeAvailable(
          context.startDate,
          context.endDate,
          context.eventRecord,
          context.resourceRecord,
        )) &&
      me.createValidatorFn.call(me.validatorFnThisObj || me, context, event)
    );
  }
  // Determine if resource already has events or not
  isRowEmpty(resourceRecord) {
    const events = this.store.getEventsForResource(resourceRecord);
    return !events || !events.length;
  }
  //endregion
  triggerBeforeFinalize(event) {
    this.client.trigger(`beforeDragCreateFinalize`, event);
  }
  /**
   * Creates an event by the event object coordinates
   * @param {Object} drag The Bryntum event object
   * @private
   */
  createEventRecord(drag) {
    const me = this,
      { client } = me,
      dimension = client.isHorizontal ? "X" : "Y",
      { timeAxis, eventStore, weekStartDay } = client,
      { event, mousedownDate } = drag,
      draggingEnd = (me.draggingEnd =
        event[`page${dimension}`] > drag.startEvent[`page${dimension}`]),
      eventConfig = {
        name:
          eventStore.modelClass.fieldMap.name.defaultValue ||
          me.L("L{Object.newEvent}"),
        startDate: draggingEnd
          ? DateHelper.floor(
              mousedownDate,
              timeAxis.resolution,
              null,
              weekStartDay,
            )
          : mousedownDate,
        endDate: draggingEnd
          ? mousedownDate
          : DateHelper.ceil(
              mousedownDate,
              timeAxis.resolution,
              null,
              weekStartDay,
            ),
      };
    if (client.project.isGanttProjectMixin) {
      ObjectHelper.assign(eventConfig, {
        constraintDate: eventConfig.startDate,
        constraintType: "startnoearlierthan",
      });
    }
    return eventStore.createRecord(eventConfig);
  }
  async internalUpdateRecord(context, eventRecord) {
    await super.internalUpdateRecord(context, eventRecord);
    if (!this.client.hasEventEditor) {
      context.eventRecord.isCreating = false;
    }
  }
  async finalizeDragCreate(context) {
    const { meta } = context.eventRecord;
    meta.excludeFromLayout = false;
    meta.isDragCreating = false;
    const transferred = await super.finalizeDragCreate(context);
    if (!transferred) {
      await this.freeStm(true);
    } else {
      this.hasStmCapture = false;
    }
    return transferred;
  }
  async cancelDragCreate(context) {
    await super.cancelDragCreate(context);
    await this.freeStm(false);
  }
  getTipHtml(...args) {
    const html = super.getTipHtml(...args),
      { element } = this.tip;
    element.classList.add("b-sch-dragcreate-tooltip");
    element.classList.toggle("b-too-narrow", this.dragging.context.tooNarrow);
    return html;
  }
  onAborted(context) {
    var _a4, _b;
    const { eventRecord, resourceRecord } = context;
    (_b = (_a4 = this.store).unassignEventFromResource) == null
      ? void 0
      : _b.call(_a4, eventRecord, resourceRecord);
    this.store.remove(eventRecord);
  }
};
//region Config
__publicField(EventDragCreate, "$name", "EventDragCreate");
__publicField(EventDragCreate, "configurable", {
  /**
   * Locks the layout during drag create, overriding the default behaviour that uses the same rendering
   * pathway for drag creation as for already existing events.
   *
   * This more closely resembles the behaviour of versions prior to 4.2.0.
   *
   * @config {Boolean} lockLayout
   * @default false
   */
  /**
   * An empty function by default, but provided so that you can perform custom validation on the event being
   * created. Return `true` if the new event is valid, `false` to prevent an event being created.
   * @param {Object} context A drag create context
   * @param {Date} context.startDate Event start date
   * @param {Date} context.endDate Event end date
   * @param {Scheduler.model.EventModel} context.record Event record
   * @param {Scheduler.model.ResourceModel} context.resourceRecord Resource record
   * @param {Event} event The event object
   * @returns {Boolean} `true` if this validation passes
   * @config {Function}
   */
  validatorFn: () => true,
});
EventDragCreate._$name = "EventDragCreate";
GridFeatureManager.registerFeature(EventDragCreate, true, "Scheduler");
