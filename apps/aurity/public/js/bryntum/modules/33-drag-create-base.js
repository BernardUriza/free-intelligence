  var _a4, _b;
  if (
    (_b =
      (_a4 = this.source) == null ? void 0 : _a4.client.features.taskEdit) ==
    null
      ? void 0
      : _b._canceling
  ) {
    return false;
  }
  return EventHelper.getDistanceBetween(this.startEvent, event);
};
var DragCreateBase = class extends EventResize.mixin(
  TaskEditStm_default,
  TransactionalFeature_default,
  TaskEditTransactional_default,
) {
  construct(scheduler, config) {
    if ((config == null ? void 0 : config.showTooltip) === false) {
      config.tip = null;
    }
    super.construct(...arguments);
  }
  //endregion
  changeValidatorFn(validatorFn) {
    this.createValidatorFn = validatorFn;
  }
  render() {
    const me = this,
      { client } = me;
    me.dragRootElement = me.dropRootElement = client.timeAxisSubGridElement;
    me.dragLock = client.isVertical ? "y" : "x";
  }
  onDragEndSwitch(context) {
    const { client } = this,
      { enableEventAnimations } = client,
      { eventRecord, draggingEnd } = context,
      horizontal = this.dragLock === "x",
      { initialDate } = this.dragging;
    client.enableEventAnimations = false;
    eventRecord.set({
      startDate: initialDate,
      endDate: initialDate,
    });
    if (draggingEnd) {
      Object.assign(context, {
        endDate: initialDate,
        toSet: "startDate",
        otherEnd: "endDate",
        setMethod: "setStartDate",
        setOtherMethod: "setEndDate",
        edge: horizontal ? "left" : "top",
      });
    } else {
      Object.assign(context, {
        startDate: initialDate,
        toSet: "endDate",
        otherEnd: "startDate",
        setMethod: "setEndDate",
        setOtherMethod: "setStartDate",
        edge: horizontal ? "right" : "bottom",
      });
    }
    context.draggingEnd = this.draggingEnd = !draggingEnd;
    client.enableEventAnimations = enableEventAnimations;
  }
  beforeDrag(drag) {
    const me = this,
      result = super.beforeDrag(drag),
      { pan, eventDragSelect } = me.client.features;
    if (
      result !== false && // used by gantt to only allow one task per row
      ((me.preventMultiple && !me.isRowEmpty(drag.rowRecord)) ||
        me.disabled || // If Pan is enabled, it has right of way
        (pan && !pan.disabled) || // If EventDragSelect is enabled, it has right of way
        (eventDragSelect && !eventDragSelect.disabled))
    ) {
      return false;
    }
    me.client.preventDragSelect = true;
    return result;
  }
  startDrag(drag) {
    const result = super.startDrag(drag);
    if (result !== false) {
      const { context } = drag;
      drag.initialDate = context.eventRecord.get(
        this.draggingEnd ? "startDate" : "endDate",
      );
      this.client.trigger("dragCreateStart", {
        proxyElement: drag.element,
        eventElement: drag.element,
        eventRecord: context.eventRecord,
        resourceRecord: context.resourceRecord,
      });
      drag.context.offset = 0;
      drag.context.oldValue = drag.mousedownDate;
    }
    return result;
  }
  // Used by our EventResize superclass to know whether the drag point is the end or the beginning.
  isOverEndHandle() {
    return this.draggingEnd;
  }
  setupDragContext(event) {
    var _a4;
    const { client } = this;
    if (client.matchScheduleCell(event.target)) {
      const resourceRecord =
        (_a4 = client.resolveResourceRecord(event)) == null
          ? void 0
          : _a4.$original;
      if (resourceRecord && !resourceRecord.isSpecialRow) {
        const result = Draggable_default().prototype.setupDragContext.call(
            this,
            event,
          ),
          scrollables = [];
        if (client.isVertical) {
          scrollables.push({
            element: client.scrollable.element,
            direction: "vertical",
          });
        } else {
          scrollables.push({
            element: client.timeAxisSubGrid.scrollable.element,
            direction: "horizontal",
          });
        }
        result.scrollManager = client.scrollManager;
        result.monitoringConfig = { scrollables };
        result.resourceRecord = result.rowRecord = resourceRecord;
        result.getDistance = getDragCreateDragDistance;
        return result;
      }
    }
  }
  async dragDrop({ context, event }) {
    var _a4;
    context[context.toSet] = context.snappedDate;
    const { client } = this,
      { startDate, endDate, eventRecord } = context,
      { generation } = eventRecord;
    let modified;
    (_a4 = this.tip) == null ? void 0 : _a4.hide();
    await client.project.commitAsync();
    if (eventRecord.generation !== generation) {
      context.eventRecord[context.toSet] = context.oldValue;
      context.eventRecord[context.toSet] = context[context.toSet];
    }
    context.valid =
      startDate &&
      endDate &&
      endDate - startDate > 0 && // Input sanity check
      context[context.toSet] - context.oldValue && // Make sure dragged end changed
      context.valid !== false;
    if (context.valid) {
      client.trigger("beforeDragCreateFinalize", {
        context,
        event,
        proxyElement: context.element,
        eventElement: context.element,
        eventRecord: context.eventRecord,
        resourceRecord: context.resourceRecord,
      });
      modified = true;
    }
    if (!context.async) {
      await context.finalize(modified);
    }
  }
  updateDragTolerance(dragTolerance) {
    this.dragThreshold = dragTolerance;
  }
  //region Tooltip
  changeTip(tip, oldTip) {
    return super.changeTip(
      !tip || tip.isTooltip
        ? tip
        : ObjectHelper.assign(
            {
              id: `${this.client.id}-drag-create-tip`,
            },
            tip,
          ),
      oldTip,
    );
  }
  //endregion
  //region Finalize (create EventModel)
  // this method is actually called on the `context` object,
  // so `this` object inside might not be what you think (see `me = this.owner` below)
  // not clear what was the motivation for such design
  async finalize(doCreate) {
    var _a4;
    if (this.finalized) {
      return;
    }
    this.finalized = true;
    const me = this.owner,
      context = this,
      completeFinalization = () => {
        if (!me.isDestroyed) {
          me.client.trigger("afterDragCreate", {
            proxyElement: context.element,
            eventElement: context.element,
            eventRecord: context.eventRecord,
            resourceRecord: context.resourceRecord,
          });
          me.cleanup(context);
        }
      };
    if (doCreate) {
      await me.finalizeDragCreate(context);
      completeFinalization();
    } else {
      await me.cancelDragCreate(context);
      (_a4 = me.onAborted) == null ? void 0 : _a4.call(me, context);
      completeFinalization();
    }
  }
  async cancelDragCreate(context) {}
  async finalizeDragCreate(context) {
    var _a4, _b;
    await this.internalUpdateRecord(context, context.eventRecord);
    const stmCapture = this.getStmCapture();
    (_a4 = this.client) == null
      ? void 0
      : _a4.trigger("dragCreateEnd", {
          eventRecord: context.eventRecord,
          resourceRecord: context.resourceRecord,
          event: context.event,
          eventElement: context.element,
          stmCapture,
        });
    (_b = this.client) == null
      ? void 0
      : _b.trigger("eventAutoCreated", {
          eventRecord: context.eventRecord,
          resourceRecord: context.resourceRecord,
        });
    return stmCapture.transferred;
  }
  cleanup(context) {
    var _a4;
    const { client } = this,
      { eventRecord } = context;
    eventRecord.meta.isResizing = false;
    client.endListeningForBatchedUpdates();
    (_a4 = this.tip) == null ? void 0 : _a4.hide();
    client.element.classList.remove(...this.dragActiveCls.split(" "));
    context.element.parentElement.classList.remove("b-sch-dragcreating");
  }
  //endregion
  //region Events
  /**
   * Prevent right click when drag creating
   * @returns {Boolean}
   * @private
   */
  onElementContextMenu() {
    if (this.proxy) {
      return false;
    }
  }
  prepareCreateContextForFinalization(
    createContext,
    event,
    finalize,
    async = false,
  ) {
    return {
      ...createContext,
      async,
      event,
      finalize,
    };
  }
  // Apply drag create "proxy" styling
  onEventDataGenerated(renderData) {
    var _a4, _b;
    if (
      ((_b = (_a4 = this.dragging) == null ? void 0 : _a4.context) == null
        ? void 0
        : _b.eventRecord) === renderData.eventRecord
    ) {
      renderData.wrapperCls["b-sch-dragcreating"] = true;
      renderData.wrapperCls["b-too-narrow"] = this.dragging.context.tooNarrow;
    }
  }
  //endregion
  //region Product specific, implemented in subclasses
  // Empty implementation here. Only base EventResize class triggers this
  triggerBeforeResize() {}
  // Empty implementation here. Only base EventResize class triggers this
  triggerEventResizeStart() {}
  checkValidity(context, event) {
    throw new Error("Implement in subclass");
  }
  handleBeforeDragCreate(dateTime, event) {
    throw new Error("Implement in subclass");
  }
  isRowEmpty(rowRecord) {
    throw new Error("Implement in subclass");
  }
  //endregion
};
//region Config
__publicField(DragCreateBase, "configurable", {
  /**
   * true to show a time tooltip when dragging to create a new event
   * @config {Boolean}
   * @default
   */
  showTooltip: true,
  /**
   * Number of pixels the drag target must be moved before dragging is considered to have started. Defaults to 2.
   * @config {Number}
   * @default
   */
  dragTolerance: 2,
  // used by gantt to only allow one task per row
  preventMultiple: false,
  dragTouchStartDelay: 300,
  /**
   * `this` reference for the validatorFn
   * @config {Object}
   */
  validatorFnThisObj: null,
  tipTemplate: (data) => `
            <div class="b-sch-tip-${data.valid ? "valid" : "invalid"}">
                ${data.startClockHtml}
                ${data.endClockHtml}
                <div class="b-sch-tip-message">${data.message}</div>
            </div>
        `,
  dragActiveCls: "b-dragcreating",
});
__publicField(DragCreateBase, "pluginConfig", {
  chain: ["render", "onEventDataGenerated"],
  before: ["onElementContextMenu"],
});
DragCreateBase._$name = "DragCreateBase";

// ../Scheduler/lib/Scheduler/feature/base/EditBase.js
var DH3 = DateHelper;
var scheduleFields = ["startDate", "endDate", "resource", "recurrenceRule"];
var makeDate = (fields) => {
  if (fields.length === 1) return fields[0].value;
  else if (fields.length === 2) {
    const [date, time] =
        fields[0] instanceof DateField ? fields : fields.reverse(),
      dateValue = DH3.parse(date.value);
    if (dateValue && time.value) {
      dateValue.setHours(
        time.value.getHours(),
        time.value.getMinutes(),
        time.value.getSeconds(),
        time.value.getMilliseconds(),
      );
    }
    return dateValue ? DateHelper.clone(dateValue) : null;
  }
  return null;
};
var copyTime = (dateTo, dateFrom) => {
  const d = new Date(dateTo.getTime());
  d.setHours(dateFrom.getHours(), dateFrom.getMinutes());
  return d;
};
var adjustEndDate = (startDate, startTime, me) => {
  if (
    !me.editor.assigningValues &&
    startDate &&
    startTime &&
    me.endDateField &&
    me.endTimeField
  ) {
    const newEndDate = DH3.add(
      copyTime(me.startDateField.value, me.startTimeField.value),
      me._durationMS,
      "milliseconds",
    );
    me.endDateField.value = newEndDate;
    me.endTimeField.value = DH3.clone(newEndDate);
  }
};
var EditBase = class extends InstancePlugin {
  //region Config
  static get configurable() {
    return {
      /**
       * True to save and close this panel if ENTER is pressed in one of the input fields inside the panel.
       * @config {Boolean}
       * @default
       * @category Editor
       */
      saveAndCloseOnEnter: true,
      triggerEvent: null,
      /**
       * This config parameter is passed to the `startDateField` and `endDateField` constructor.
       * @config {String}
       * @default
       * @category Editor widgets
       */
      dateFormat: "L",
      // date format that uses browser locale
      /**
       * This config parameter is passed to the `startTimeField` and `endTimeField` constructor.
       * @config {String}
       * @default
       * @category Editor widgets
       */
      timeFormat: "LT",
      // date format that uses browser locale
      /**
       * Default editor configuration, which widgets it shows etc.
       *
       * This is the entry point into configuring any aspect of the editor.
       *
       * The {@link Core.widget.Container#config-items} configuration of a Container
       * is *deeply merged* with its default `items` value. This means that you can specify
       * an `editorConfig` object which configures the editor, or widgets inside the editor:
       * ```javascript
       * const scheduler = new Scheduler({
       *     features : {
       *         eventEdit  : {
       *             editorConfig : {
       *                 autoClose : false,
       *                 modal     : true,
       *                 cls       : 'editor-widget-cls',
       *                 items : {
       *                     resourceField : {
       *                         hidden : true
       *                     },
       *                     // Add our own event owner field at the top of the form.
       *                     // Weight -100 will make it sort top the top.
       *                     ownerField : {
       *                         weight : -100,
       *                         type   : 'usercombo',
       *                         name   : 'owner',
       *                         label  : 'Owner'
       *                     }
       *                 },
       *                 bbar : {
       *                     items : {
       *                         deleteButton : false
       *                     }
       *                 }
       *             }
       *         }
       *     }
       * });
       * ```
       * @config {PopupConfig}
       * @category Editor
       */
      editorConfig: null,
      /**
       * An object to merge with the provided items config of the editor to override the
       * configuration of provided fields, or add new fields.
       *
       * To remove existing items, set corresponding keys to `null`:
       *
       * ```javascript
       * const scheduler = new Scheduler({
       *     features : {
       *         eventEdit  : {
       *             items : {
       *                 // Merged with provided config of the resource field
       *                 resourceField : {
       *                     label : 'Calendar'
       *                 },
       *                 recurrenceCombo : null,
       *                 owner : {
       *                     weight : -100, // Will sort above system-supplied fields which are weight 0
       *                     type   : 'usercombo',
       *                     name   : 'owner',
       *                     label  : 'Owner'
       *                 }
       *             }
       *         }
       *     }
       * });
       *```
       *
       * The provided fields are called
       *  - `nameField`
       *  - `resourceField`
       *  - `startDateField`
       *  - `startTimeField`
       *  - `endDateField`
       *  - `endTimeField`
       *  - `recurrenceCombo`
       *  - `editRecurrenceButton`
       * @config {Object<String,ContainerItemConfig|Boolean|null>}
       * @category Editor widgets
       */
      items: null,
      /**
       * The week start day used in all date fields of the feature editor form by default.
       * 0 means Sunday, 6 means Saturday.
       * Defaults to the locale's week start day.
       * @config {Number}
       */
      weekStartDay: null,
    };
  }
  //endregion
  //region Init & destroy
  construct(client, config) {
    const me = this;
    client.eventEdit = me;
    super.construct(
      client,
      ObjectHelper.assign(
        {
          weekStartDay: client.weekStartDay,
        },
        config,
      ),
    );
    me.clientListenersDetacher = client.ion({
      [me.triggerEvent]: "onActivateEditor",
      dragCreateEnd: "onDragCreateEnd",
      // Not fired at the Scheduler level.
      // Calendar, which inherits this, implements this event.
      eventAutoCreated: "onEventAutoCreated",
      thisObj: me,
    });
  }
  doDestroy() {
    var _a4;
    this.clientListenersDetacher();
    (_a4 = this._editor) == null ? void 0 : _a4.destroy();
    super.doDestroy();
  }
  //endregion
  //region Editing
  // Not implemented at this level.
  // Scheduler Editing relies on being called at point of event creation.
  onEventAutoCreated() {}
  changeEditorConfig(editorConfig) {
    const { items: items2 } = this;
    if (items2) {
      editorConfig = Objects.clone(editorConfig);
      editorConfig.items = Config.merge(items2, editorConfig.items);
    }
    return editorConfig;
  }
  changeItems(items2) {
    this.cleanItemsConfig(items2);
    return items2;
  }
  // Remove any items configured as === true which just means default config options
  cleanItemsConfig(items2) {
    for (const ref in items2) {
      const itemCfg = items2[ref];
      if (itemCfg === true) {
        delete items2[ref];
      } else if (itemCfg == null ? void 0 : itemCfg.items) {
        this.cleanItemsConfig(itemCfg.items);
      }
    }
  }
  onDatesChange({ value, source }) {
    var _a4, _b, _c, _d, _e, _f, _g, _h, _i, _j;
    const me = this;
    if (
      (source === me.endDateField || source === me.endTimeField) &&
      me.startDateField
    ) {
      const newEndDate =
          ((_a4 = me.endTimeField) == null ? void 0 : _a4.value) &&
          ((_b = me.endDateField) == null ? void 0 : _b.value)
            ? copyTime(me.endDateField.value, me.endTimeField.value)
            : (_c = me.endDateField) == null
              ? void 0
              : _c.value,
        newStartDate =
          ((_d = me.startTimeField) == null ? void 0 : _d.value) &&
          ((_e = me.startDateField) == null ? void 0 : _e.value)
            ? copyTime(me.startDateField.value, me.startTimeField.value)
            : (_f = me.startDateField) == null
              ? void 0
              : _f.value;
      if (newEndDate && newStartDate) {
        me._durationMS = newEndDate - newStartDate;
      }
    }
    if (me.startDateField && me.endDateField) {
      me.endDateField.min = me.startDateField.value;
    }
    if (me.endTimeField) {
      if (
        DH3.isEqual(
          DH3.clearTime((_g = me.startDateField) == null ? void 0 : _g.value),
          DH3.clearTime((_h = me.endDateField) == null ? void 0 : _h.value),
        )
      ) {
        me.endTimeField.min = me.startTimeField.value;
      } else {
        me.endTimeField.min = null;
      }
    }
    switch (source.ref) {
      case "startDateField":
        ((_i = me.startTimeField) == null ? void 0 : _i.value) &&
          adjustEndDate(value, me.startTimeField.value, me);
        break;
      case "startTimeField":
        ((_j = me.startDateField) == null ? void 0 : _j.value) &&
          adjustEndDate(me.startDateField.value, value, me);
        break;
    }
  }
  //endregion
  //region Save
  async save() {
    throw new Error("Implement in subclass");
  }
  get values() {
    const me = this,
      { editor } = me,
      startFields = [],
      endFields = [],
      { values } = editor;
    scheduleFields.forEach((f) => delete values[f]);
    editor.eachWidget((widget) => {
      var _a4;
      const { name } = widget;
      if (
        !name ||
        widget.hidden ||
        widget.up((w) => w === me.recurrenceEditor)
      ) {
        delete values[name];
        return;
      }
      switch (name) {
        case "startDate":
          startFields.push(widget);
          break;
        case "endDate":
          endFields.push(widget);
          break;
        case "resource":
          values[name] = widget.record;
          break;
        case "recurrenceRule":
          values[name] =
            ((_a4 = editor.widgetMap.recurrenceCombo) == null
              ? void 0
              : _a4.value) === "none"
              ? ""
              : widget.value;
          break;
      }
    }, true);
    if (values.allDay && !me.eventRecord.allDay) {
      startFields.push(me.startTimeField);
      endFields.push(me.endTimeField);
    }
    if (startFields.length) {
      values.startDate = makeDate(startFields);
    }
    if (endFields.length) {
      values.endDate = makeDate(endFields);
    }
    if ("startDate" in values && "endDate" in values) {
      values.duration = DH3.diff(
        values.startDate,
        values.endDate,
        me.editor.record.durationUnit,
        true,
      );
    }
    return values;
  }
  /**
   * Template method, intended to be overridden. Called before the event record has been updated.
   * @param {Scheduler.model.EventModel} eventRecord The event record
   *
   **/
  onBeforeSave(eventRecord) {}
  /**
   * Template method, intended to be overridden. Called after the event record has been updated.
   * @param {Scheduler.model.EventModel} eventRecord The event record
   *
   **/
  onAfterSave(eventRecord) {}
  /**
   * Updates record being edited with values from the editor
   * @private
   */
  updateRecord(record) {
    var _a4;
    const { values } = this;
    if (this.assignmentStore) {
      delete values.resource;
    }
    this._durationMS = DateHelper.asMilliseconds(
      (_a4 = values.duration) != null ? _a4 : record.duration,
      record.durationUnit,
    );
    return record.set(values);
  }
  //endregion
  //region Events
  onBeforeEditorShow() {
    const { eventRecord, editor } = this.editingContext,
      { nameField } = editor.widgetMap;
    if (nameField && eventRecord.isCreating) {
      editor.assigningValues = true;
      nameField.value = "";
      editor.assigningValues = false;
      nameField._configuredPlaceholder = nameField.placeholder;
      nameField.placeholder = eventRecord.name;
    }
  }
  resetEditingContext() {
    var _a4;
    const me = this;
    if (!me.editingContext) {
      return;
    }
    const { client } = me,
      { editor, eventRecord } = me.editingContext,
      { eventStore } = client,
      { nameField } = editor.widgetMap;
    if (eventRecord.isCreating) {
      if (client.isTimelineBase) {
        (_a4 = me.editingContext.eventElement) == null
          ? void 0
          : _a4.closest("[data-event-id]").classList.add("b-released");
      }
      eventStore.remove(eventRecord);
      eventRecord.isCreating = false;
    }
    if (nameField) {
      nameField.placeholder = nameField._configuredPlaceholder;
    }
    client.element.classList.remove("b-eventeditor-editing");
    me.targetEventElement = me.editingContext = editor._record = null;
  }
  onPopupKeyDown({ event }) {
    const me = this;
    if (
      !me.readOnly &&
      event.key === "Enter" &&
      me.saveAndCloseOnEnter &&
      event.target.tagName.toLowerCase() === "input"
    ) {
      event.preventDefault();
      if (event.target.name === "startDate") {
        me.startTimeField &&
          adjustEndDate(me.startDateField.value, me.startTimeField.value, me);
      }
      me.onSaveClick();
    }
  }
  async finalizeStmCapture(saved) {}
  async onSaveClick() {
    this.editor.focus();
    this.isFinalizingEventSave = true;
    const saved = await this.save();
    this.isFinalizingEventSave = false;
    if (saved) {
      await this.finalizeStmCapture(false);
      this.editor.close();
      this.client.trigger("afterEventEdit");
    }
    return saved;
  }
  async onDeleteClick() {
    this.isDeletingEvent = true;
    const removed = await this.deleteEvent();
    this.isDeletingEvent = false;
    if (removed) {
      await this.finalizeStmCapture(false);
      const { editor } = this;
      if (!editor.autoClose || editor.containsFocus) {
        editor.close();
      }
      this.client.trigger("afterEventEdit");
    }
  }
  async onCancelClick() {
    this.isCancelingEdit = true;
    this.editor.close();
    this.isCancelingEdit = false;
    if (this.hasStmCapture) {
      await this.finalizeStmCapture(true);
    }
    this.client.trigger("afterEventEdit");
  }
  //endregion
};
EditBase._$name = "EditBase";

// ../Scheduler/lib/Scheduler/feature/base/ResourceTimeRangesBase.js
var ResourceTimeRangesBase = class extends InstancePlugin.mixin(
  AttachToProjectMixin_default,
) {
  static get pluginConfig() {
    return {
      chain: [
        "getEventsToRender",
        "onEventDataGenerated",
        "noFeatureElementsInAxis",
      ],
      override: ["matchScheduleCell", "resolveResourceRecord"],
    };
  }
  // Let Scheduler know if we have ResourceTimeRanges in view or not
  noFeatureElementsInAxis() {
    const { timeAxis } = this.client;
    return (
      !this.needsRefresh &&
      this.store &&
      !this.store.storage.values.some((t) => timeAxis.isTimeSpanInAxis(t))
    );
  }
  //endregion
  //region Init
  doDisable(disable) {
    if (this.client.isPainted) {
      this.client.refresh();
    }
    super.doDisable(disable);
  }
  updateTabIndex() {
    if (!this.isConfiguring) {
      this.client.refresh();
    }
  }
  //endregion
  getEventsToRender(resource, events) {
    throw new Error("Implement in subclass");
  }
  // Called for each event during render, allows manipulation of render data. Adjust any resource time ranges
  // (chained function from Scheduler)
  onEventDataGenerated(renderData) {
    const me = this,
      { client } = me,
      { eventRecord, iconCls } = renderData;
    if (me.shouldInclude(eventRecord)) {
      if (client.isVertical) {
        renderData.width = client.getResourceWidth(renderData.resourceRecord);
      } else {
        renderData.top = 0;
      }
      renderData.fillSize = true;
      renderData.wrapperCls["b-sch-resourcetimerange"] = 1;
      if (me.rangeCls) {
        renderData.wrapperCls[me.rangeCls] = 1;
      }
      renderData.wrapperCls[`b-sch-color-${eventRecord.timeRangeColor}`] =
        eventRecord.timeRangeColor;
      me.renderContent(eventRecord, renderData);
      renderData.children.push(renderData.eventContent);
      renderData.tabIndex = me.tabIndex != null ? String(me.tabIndex) : null;
      if ((iconCls == null ? void 0 : iconCls.length) > 0) {
        renderData.children.unshift({
          tag: "i",
          className: iconCls.toString(),
        });
      }
      renderData.eventId = me.generateElementId(eventRecord);
    }
  }
  renderContent(eventRecord, renderData) {
    renderData.eventContent.text = eventRecord.name;
  }
  /**
   * Generates ID from the passed time range record
   * @param {Scheduler.model.TimeSpan} record
   * @returns {String} Generated ID for the DOM element
   * @internal
   */
  generateElementId(record) {
    return record.domId;
  }
  resolveResourceTimeRangeRecord(rangeElement) {
    var _a4;
    return (_a4 =
      rangeElement == null
        ? void 0
        : rangeElement.closest(`.${this.rangeCls}`)) == null
      ? void 0
      : _a4.elementData.eventRecord;
  }
  getElementFromResourceTimeRangeRecord(record) {
    return this.client.foregroundCanvas.syncIdMap[record.domId];
  }
  resolveResourceRecord(event) {
    var _a4;
    const record = this.overridden.resolveResourceRecord(...arguments);
    return (
      record ||
      ((_a4 = this.resolveResourceTimeRangeRecord(event.target || event)) ==
      null
        ? void 0
        : _a4.resource)
    );
  }
  shouldInclude(eventRecord) {
    throw new Error("Implement in subclass");
  }
  // Called when a ResourceTimeRangeModel is manipulated, relays to Scheduler#onInternalEventStoreChange which updates to UI
  onStoreChange(event) {
    if (event.action === "removeall" || event.action === "dataset") {
      this.needsRefresh = true;
    }
    this.client.onInternalEventStoreChange(event);
    this.needsRefresh = false;
  }
  // Override to let scheduler find the time cell from a resource time range element
  matchScheduleCell(target) {
    let cell = this.overridden.matchScheduleCell(target);
    if (!cell && this.enableMouseEvents) {
      const { client } = this,
        rangeElement = target.closest(`.${this.rangeCls}`);
      cell =
        rangeElement &&
        client.getCell({
          record: client.isHorizontal
            ? rangeElement.elementData.resource
            : client.store.first,
          column: client.timeAxisColumn,
        });
    }
    return cell;
  }
  handleRangeMouseEvent(domEvent) {
    var _a4;
    const me = this,
      rangeElement = domEvent.target.closest(`.${me.rangeCls}`);
    if (rangeElement) {
      const eventName =
          (_a4 = EventHelper.eventNameMap[domEvent.type]) != null
            ? _a4
            : StringHelper.capitalize(domEvent.type),
        resourceTimeRangeRecord =
          me.resolveResourceTimeRangeRecord(rangeElement);
      me.client.trigger(me.entityName + eventName, {
        feature: me,
        [`${me.entityName}Record`]: resourceTimeRangeRecord,
        resourceRecord: me.client.resourceStore.getById(
          resourceTimeRangeRecord.resourceId,
        ),
        domEvent,
      });
    }
  }
  updateEnableMouseEvents(enable) {
    var _a4;
    const me = this,
      { client } = me;
    (_a4 = me.mouseEventsDetacher) == null ? void 0 : _a4.call(me);
    me.mouseEventsDetacher = null;
    if (enable) {
      let attachMouseEvents = function () {
        me.mouseEventsDetacher = EventHelper.on({
          element: client.foregroundCanvas,
          delegate: `.${me.rangeCls}`,
          mousedown: "handleRangeMouseEvent",
          mouseup: "handleRangeMouseEvent",
          click: "handleRangeMouseEvent",
          dblclick: "handleRangeMouseEvent",
          contextmenu: "handleRangeMouseEvent",
          mouseover: "handleRangeMouseEvent",
          mouseout: "handleRangeMouseEvent",
          thisObj: me,
        });
      };
      client.whenVisible(attachMouseEvents);
    }
    client.element.classList.toggle(
      "b-interactive-resourcetimeranges",
      Boolean(enable),
    );
  }
};
//region Config
__publicField(ResourceTimeRangesBase, "configurable", {
  /**
   * Specify value to use for the tabIndex attribute of range elements
   * @config {Number}
   * @category Misc
   */
  tabIndex: null,
  entityName: "resourceTimeRange",
});
ResourceTimeRangesBase.featureClass = "";
ResourceTimeRangesBase._$name = "ResourceTimeRangesBase";

// ../Scheduler/lib/Scheduler/feature/base/TimeSpanMenuBase.js
var TimeSpanMenuBase = class extends ContextMenuBase {};
TimeSpanMenuBase._$name = "TimeSpanMenuBase";

// ../Scheduler/lib/Scheduler/feature/base/TooltipBase.js
var TooltipBase = class extends InstancePlugin {
  //region Config
  static get defaultConfig() {
    return {
      /**
       * Specify true to have tooltip updated when mouse moves, if you for example want to display date at mouse
       * position.
       * @config {Boolean}
       * @default
       * @category Misc
       */
      autoUpdate: false,
      /**
       * The amount of time to hover before showing
       * @config {Number}
       * @default
       */
      hoverDelay: 250,
      /**
       * The time (in milliseconds) for which the Tooltip remains visible when the mouse leaves the target.
       *
       * May be configured as `false` to persist visible after the mouse exits the target element. Configure it
       * as 0 to always retrigger `hoverDelay` even when moving mouse inside `fromElement`
       * @config {Number}
       * @default
       */
      hideDelay: 100,
      template: null,
      cls: null,
      align: {
        align: "b-t",
      },
      clockTemplate: null,
      // Set to true to update tooltip contents if record changes while tip is open
      monitorRecordUpdate: null,
      testConfig: {
        hoverDelay: 0,
      },
    };
  }
  // Plugin configuration. This plugin chains some of the functions in Grid.
  static get pluginConfig() {
    return {
      chain: ["onInternalPaint"],
    };
  }
  //endregion
  //region Events
  /**
   * Triggered before a tooltip is shown. Return `false` to prevent the action.
   * @preventable
   * @event beforeShow
   * @param {Core.widget.Tooltip} source The tooltip being shown.
   * @param {Scheduler.model.EventModel} source.eventRecord The event record.
   */
  /**
   * Triggered after a tooltip is shown.
   * @event show
   * @param {Core.widget.Tooltip} source The tooltip.
   * @param {Scheduler.model.EventModel} source.eventRecord The event record.
   */
  //endregion
  //region Init
  construct(client, config) {
    const me = this;
    config = me.processConfig(config);
    super.construct(client, config);
    if (!me.forSelector) {
      me.forSelector = `${client.eventInnerSelector}:not(.b-dragproxy,.b-iscreating)`;
    }
    me.clockTemplate = new ClockTemplate({
      scheduler: client,
    });
    client.ion({
      [`before${client.scheduledEventName}drag`]: () => {
        var _a4;
        (_a4 = me.tooltip) == null ? void 0 : _a4.hide();
      },
    });
  }
  // TooltipBase feature handles special config cases, where user can supply a function to use as template
  // instead of a normal config object
  processConfig(config) {
    if (typeof config === "function") {
      return {
        template: config,
      };
    }
    return config;
  }
  // override setConfig to process config before applying it (used mainly from ReactScheduler)
  setConfig(config) {
    super.setConfig(this.processConfig(config));
  }
  doDestroy() {
    this.destroyProperties("clockTemplate", "tooltip");
    super.doDestroy();
  }
  doDisable(disable) {
    if (this.tooltip) {
      this.tooltip.disabled = disable;
    }
    super.doDisable(disable);
  }
  //endregion
  onInternalPaint({ firstPaint }) {
    var _a4;
    if (firstPaint) {
      const me = this,
        { client } = me,
        ignoreSelector = `:not(${[
          ".b-dragselecting",
          ".b-eventeditor-editing",
          ".b-taskeditor-editing",
          ".b-resizing-event",
          ".b-task-percent-bar-resizing-task",
          ".b-dragcreating",
          `.b-dragging-${client.scheduledEventName}`,
          ".b-creating-dependency",
          ".b-dragproxy",
        ].join()})`;
      (_a4 = me.tooltip) == null ? void 0 : _a4.destroy();
      const tip = (me.tooltip = new Tooltip({
        axisLock: "flexible",
        id: me.tipId || `${me.client.id}-event-tip`,
        cls: me.tipCls,
        forSelector: `.b-timelinebase${ignoreSelector} .b-grid-body-container:not(.b-scrolling) ${me.forSelector}`,
        scrollAction: "realign",
        forElement: client.timeAxisSubGridElement,
        showOnHover: true,
        anchorToTarget: true,
        getHtml: me.getTipHtml.bind(me),
        disabled: me.disabled,
        // on Core/mixin/Events constructor, me.config.listeners is deleted and attributed its value to me.configuredListeners
        // to then on processConfiguredListeners it set me.listeners to our TooltipBase
        // but since we need our initial config.listeners to set to our internal tooltip, we leave processConfiguredListeners empty
        // to avoid lost our listeners to apply for our internal tooltip here and force our feature has all Tooltip events firing
        ...me.config,
        internalListeners: me.configuredListeners,
      }));
      tip.ion({
        innerhtmlupdate: "updateDateIndicator",
        overtarget: "onOverNewTarget",
        show: "onTipShow",
        hide: "onTipHide",
        thisObj: me,
      });
      Object.keys(tip.$meta.configs).forEach((name) => {
        Object.defineProperty(this, name, {
          set: (v) => (tip[name] = v),
          get: () => tip[name],
        });
      });
    }
  }
  //region Listeners
  // leave configuredListeners alone until render time at which they are used on the tooltip
  processConfiguredListeners() {}
  addListener(...args) {
    var _a4;
    const defaultDetacher = super.addListener(...args),
      tooltipDetacher =
        (_a4 = this.tooltip) == null ? void 0 : _a4.addListener(...args);
    if (defaultDetacher || tooltipDetacher) {
      return () => {
        defaultDetacher == null ? void 0 : defaultDetacher();
        tooltipDetacher == null ? void 0 : tooltipDetacher();
      };
    }
  }
  removeListener(...args) {
    var _a4;
    super.removeListener(...args);
    (_a4 = this.tooltip) == null ? void 0 : _a4.removeListener(...args);
  }
  //endregion
  updateDateIndicator() {
    const me = this,
      tip = me.tooltip,
      endDateElement = tip.element.querySelector(".b-sch-tooltip-enddate");
    if (!me.record) {
      return;
    }
    me.clockTemplate.updateDateIndicator(tip.element, me.record.startDate);
    endDateElement &&
      me.clockTemplate.updateDateIndicator(endDateElement, me.record.endDate);
  }
  resolveTimeSpanRecord(forElement) {
    return this.client.resolveTimeSpanRecord(forElement);
  }
  getTipHtml({ tip, activeTarget }) {
    const me = this,
      { client } = me,
      recordProp = me.recordType || `${client.scheduledEventName}Record`,
      timeSpanRecord = me.resolveTimeSpanRecord(activeTarget);
    if (
      (timeSpanRecord == null ? void 0 : timeSpanRecord.startDate) instanceof
      Date
    ) {
      const { startDate, endDate } = timeSpanRecord,
        startText = client.getFormattedDate(startDate),
        endDateValue = client.getDisplayEndDate(endDate, startDate),
        endText = client.getFormattedDate(endDateValue);
      tip.eventRecord = timeSpanRecord;
      return me.template({
        tip,
        // eventRecord for Scheduler, taskRecord for Gantt
        [`${recordProp}`]: timeSpanRecord,
        startDate,
        endDate,
        startText,
        endText,
        startClockHtml: me.clockTemplate.template({
          date: startDate,
          text: startText,
          cls: "b-sch-tooltip-startdate",
        }),
        endClockHtml: timeSpanRecord.isMilestone
          ? ""
          : me.clockTemplate.template({
              date: endDateValue || "",
              text: endText || "",
              cls: "b-sch-tooltip-enddate",
            }),
      });
    } else {
      tip.hide();
      return "";
    }
  }
  get record() {
    return this.tooltip.eventRecord;
  }
  onTipShow() {
    const me = this;
    if (me.monitorRecordUpdate && !me.updateListener) {
      me.updateListener = me.client.eventStore.ion({
        change: me.onRecordUpdate,
        buffer: 300,
        thisObj: me,
      });
    }
  }
  onTipHide() {
    var _a4;
    this.tooltip.eventRecord = null;
    (_a4 = this.updateListener) == null ? void 0 : _a4.call(this);
    this.updateListener = null;
  }
  onOverNewTarget({ newTarget }) {
    const { tooltip } = this;
    if (tooltip.isVisible) {
      if (this.client.timeAxisSubGrid.scrolling || this.client.scrolling) {
        tooltip.hide(false);
      } else {
        tooltip.eventRecord = this.resolveTimeSpanRecord(newTarget);
      }
    }
  }
  onRecordUpdate({ record }) {
    const { tooltip } = this;
    if (
      (tooltip == null ? void 0 : tooltip.isVisible) &&
      record === this.record
    ) {
      tooltip.updateContent();
      if (tooltip.lastAlignSpec.aligningToElement) {
        tooltip.realign();
      } else {
        tooltip.internalOnPointerOver(this.client.lastPointerEvent);
      }
    }
  }
};
TooltipBase._$name = "TooltipBase";

// ../Scheduler/lib/Scheduler/feature/AbstractTimeRanges.js
var AbstractTimeRanges = class extends InstancePlugin.mixin(Delayable_default) {
  //region Config
  /**
   * Fired on the owning Scheduler or Gantt widget when a click happens on a time range header element
   * @event timeRangeHeaderClick
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.TimeSpan} timeRangeRecord The record
   * @param {MouseEvent} event DEPRECATED 5.3.0 Use `domEvent` instead
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler or Gantt widget when a double click happens on a time range header element
   * @event timeRangeHeaderDblClick
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.TimeSpan} timeRangeRecord The record
   * @param {MouseEvent} event DEPRECATED 5.3.0 Use `domEvent` instead
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler or Gantt widget when a right click happens on a time range header element
   * @event timeRangeHeaderContextMenu
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.TimeSpan} timeRangeRecord The record
   * @param {MouseEvent} event DEPRECATED 5.3.0 Use `domEvent` instead
   * @param {MouseEvent} domEvent Browser event
   */
  static get defaultConfig() {
    return {
      // CSS class to apply to range elements
      rangeCls: "b-sch-range",
      // CSS class to apply to line elements (0-duration time range)
      lineCls: "b-sch-line",
      /**
       * Set to `true` to enable dragging and resizing of range elements in the header. Only relevant when
       * {@link #config-showHeaderElements} is `true`.
       * @config {Boolean}
       * @default
       * @category Common
       */
      enableResizing: false,
      /**
       * A Boolean specifying whether to show tooltip while resizing range elements, or a
       * {@link Core.widget.Tooltip} config object which is applied to the tooltip
       * @config {Boolean|TooltipConfig}
       * @default
       * @category Common
       */
      showTooltip: true,
      /**
       * The Tooltip instance shown when hovering a TimeRange header element
       * @member {Core.widget.Tooltip} hoverTooltip
       * @readonly
       */
      /**
       * A {@link Core.widget.Tooltip} config object which is applied to the tooltip shown when hovering a
       * TimeRange header element
       * @config {TooltipConfig}
       * @category Common
       */
      hoverTooltip: null,
      /**
       * Template used to generate the tooltip contents when hovering a time range header element.
       *
       * ```javascript
       * const scheduler = new Scheduler({
       *   features : {
       *     timeRanges : {
       *       tooltipTemplate({ timeRange }) {
       *         return `${timeRange.name}`
       *       }
       *     }
       *   }
       * });
       * ```
       *
       * @config {Function} tooltipTemplate
       * @param {Object} data Tooltip data
       * @param {Scheduler.model.TimeSpan} data.timeRange
       * @param {String} data.startClockHtml Predefined HTML to show the start time
       * @param {String} data.endClockHtml Predefined HTML to show the end time
       * @returns {String} String representing the HTML markup
       * @category Common
       */
      tooltipTemplate: null,
      dragTipTemplate: (data) => `
                <div class="b-sch-tip-${data.valid ? "valid" : "invalid"}">
                    <div class="b-sch-tip-name">${StringHelper.encodeHtml(data.name) || ""}</div>
                    ${data.startClockHtml}
                    ${data.endClockHtml || ""}
                </div>
            `,
      baseCls: "b-sch-timerange",
      /**
       * Function used to generate the HTML content for a time range header element.
       *
       * ```javascript
       * const scheduler = new Scheduler({
       *   features : {
       *     timeRanges : {
       *       headerRenderer({ timeRange }) {
       *         return `${timeRange.name}`
       *       }
       *     }
       *   }
       * });
       * ```
       *
       * @config {Function} headerRenderer
       * @param {Object} data Render data
       * @param {Scheduler.model.TimeSpan} data.timeRange
       * @returns {String} String representing the HTML markup
       *
       * @category Common
       */
      headerRenderer: null,
      /**
       * Function used to generate the HTML content for a time range body element.
       *
       * ```javascript
       * const scheduler = new Scheduler({
       *   features : {
       *     timeRanges : {
       *       bodyRenderer({ timeRange }) {
       *         return `${timeRange.name}`
       *       }
       *     }
       *   }
       * });
       * ```
       *
       * @config {Function} bodyRenderer
       * @param {Object} data Render data
       * @param {Scheduler.model.TimeSpan} data.timeRange
       * @returns {String} String representing the HTML markup
       *
       * @category Common
       */
      bodyRenderer: null,
      // a unique cls used by subclasses to get custom styling of the elements rendered
      cls: null,
      narrowThreshold: 80,
    };
  }
  //endregion
  //region Init & destroy
  construct(client, config) {
    const me = this;
    super.construct(client, config);
    if (client.isVertical) {
      client.ion({
        renderRows: me.onUIReady,
        thisObj: me,
        once: true,
      });
    }
    me.cls = me.cls || `b-sch-${me.constructor.$$name.toLowerCase()}`;
    me.baseSelector = `.${me.baseCls}.${me.cls}`;
    if (me.enableResizing) {
      me.showHeaderElements = true;
    }
  }
  doDestroy() {
    var _a4, _b, _c, _d;
    const me = this;
    me.detachListeners("timeAxisViewModel");
    me.detachListeners("timeAxis");
    (_a4 = me.clockTemplate) == null ? void 0 : _a4.destroy();
    (_b = me.tip) == null ? void 0 : _b.destroy();
    (_c = me.drag) == null ? void 0 : _c.destroy();
    (_d = me.resize) == null ? void 0 : _d.destroy();
    super.doDestroy();
  }
  doDisable(disable) {
    this.renderRanges();
    super.doDisable(disable);
  }
  setupTimeAxisViewModelListeners() {
    const me = this;
    me.detachListeners("timeAxisViewModel");
    me.detachListeners("timeAxis");
    me.client.timeAxisViewModel.ion({
      name: "timeAxisViewModel",
      update: "onTimeAxisViewModelUpdate",
      thisObj: me,
    });
    me.client.timeAxis.ion({
      name: "timeAxis",
      includeChange: "renderRanges",
      thisObj: me,
    });
    me.updateLineBuffer();
  }
  onUIReady() {
    const me = this,
      { client } = me;
    client.ion({
      timeAxisViewModelChange: me.setupTimeAxisViewModelListeners,
      thisObj: me,
    });
    me.setupTimeAxisViewModelListeners();
    if (!client.hideHeaders) {
      if (me.headerContainerElement) {
        EventHelper.on({
          click: me.onTimeRangeClick,
          dblclick: me.onTimeRangeClick,
          contextmenu: me.onTimeRangeClick,
          delegate: me.baseSelector,
          element: me.headerContainerElement,
          thisObj: me,
        });
      }
      if (me.enableResizing) {
        me.drag = DragHelper.new(
          {
            name: "rangeDrag",
            lockX: client.isVertical,
            lockY: client.isHorizontal,
            constrain: true,
            outerElement: me.headerContainerElement,
            targetSelector: `${me.baseSelector}`,
            isElementDraggable: (el, event) =>
              !client.readOnly && me.isElementDraggable(el, event),
            rtlSource: client,
            internalListeners: {
              dragstart: "onDragStart",
              drag: "onDrag",
              drop: "onDrop",
              reset: "onDragReset",
              abort: "onInvalidDrop",
              thisObj: me,
            },
          },
          me.dragHelperConfig,
        );
        me.resize = ResizeHelper.new(
          {
            direction: client.mode,
            targetSelector: `${me.baseSelector}.b-sch-range`,
            outerElement: me.headerContainerElement,
            isElementResizable: (el, event) =>
              !el.matches(".b-dragging,.b-readonly") &&
              !event.target.matches(".b-fa"),
            internalListeners: {
              resizestart: "onResizeStart",
              resizing: "onResizeDrag",
              resize: "onResize",
              cancel: "onInvalidResize",
              reset: "onResizeReset",
              thisObj: me,
            },
          },
          me.resizeHelperConfig,
        );
      }
    }
    me.renderRanges();
    if (me.tooltipTemplate) {
      me.hoverTooltip = new Tooltip(
        ObjectHelper.assign(
          {
            forElement: me.headerContainerElement,
            getHtml({ activeTarget }) {
              const timeRange = me.resolveTimeRangeRecord(activeTarget);
              return me.tooltipTemplate({ timeRange });
            },
            forSelector: `.b-timelinebase:not(.b-dragging-timerange, .b-resizing-timerange) .${me.baseCls}${me.cls ? "." + me.cls : ""}`,
          },
          me.hoverTooltip,
        ),
      );
    }
  }
  //endregion
  //region Draw
  refresh() {
    this._timeRanges = null;
    this.renderRanges();
  }
  getDOMConfig(startDate, endDate) {
    const me = this,
      bodyConfigs = [],
      headerConfigs = [];
    if (!me.disabled) {
      me._labelRotationMap = {};
      for (const range of me.timeRanges) {
        const result = me.renderRange(range, startDate, endDate);
        if (result) {
          bodyConfigs.push(result.bodyConfig);
          headerConfigs.push(result.headerConfig);
        }
      }
    }
    return [bodyConfigs, headerConfigs];
  }
  renderRanges() {
    const me = this,
      { client } = me;
    if (client.isPainted && !client.timeAxisSubGrid.collapsed) {
      const { headerContainerElement } = me,
        updatedBodyElements = [],
        [bodyConfigs, headerConfigs] = me.getDOMConfig();
      if (!me.bodyCanvas) {
        me.bodyCanvas = DomHelper.createElement({
          className: `b-timeranges-canvas b-timeranges-body-canvas ${me.cls}-canvas b-sch-canvas`,
          parent: client.timeAxisSubGridElement,
          retainElement: true,
        });
      }
      DomSync.sync({
        targetElement: me.bodyCanvas,
        domConfig: {
          children: bodyConfigs,
          onlyChildren: true,
          syncOptions: {
            releaseThreshold: 0,
            syncIdField: "id",
          },
        },
        callback: me.showHeaderElements
          ? null
          : ({ targetElement, action }) => {
              if (
                action === "reuseElement" ||
                action === "newElement" ||
                action === "reuseOwnElement"
              ) {
                updatedBodyElements.push(targetElement);
              }
            },
      });
      if (me.showHeaderElements && !me.headerCanvas) {
        me.headerCanvas = DomHelper.createElement({
          className: `b-timeranges-canvas b-timeranges-header-canvas ${me.cls}-canvas`,
          parent: headerContainerElement,
          retainElement: true,
        });
      }
      if (me.headerCanvas) {
        DomSync.sync({
          targetElement: me.headerCanvas,
          domConfig: {
            onlyChildren: true,
            children: headerConfigs,
            syncOptions: {
              releaseThreshold: 0,
              syncIdField: "id",
            },
          },
        });
      }
      for (const bodyElement of updatedBodyElements) {
        me.cacheRotation(bodyElement.elementData.timeRange, bodyElement);
      }
      for (const bodyElement of updatedBodyElements) {
        me.applyRotation(bodyElement.elementData.timeRange, bodyElement);
      }
    }
  }
  // Implement in subclasses
  get timeRanges() {
    return [];
  }
  /**
   * Based on this method result the feature decides whether the provided range should
   * be rendered or not.
   * The method checks that the range intersects the current viewport.
   *
   * Override the method to implement your custom range rendering vetoing logic.
   * @param {Scheduler.model.TimeSpan} range Range to render.
   * @param {Date} [startDate] Specifies view start date. Defaults to view visible range start
   * @param {Date} [endDate] Specifies view end date. Defaults to view visible range end
   * @returns {Boolean} `true` if the range should be rendered and `false` otherwise.
   */
  shouldRenderRange(
    range,
    startDate = this.client.visibleDateRange.startDate,
    endDate = this.client.visibleDateRange.endDate,
  ) {
    const { timeAxis } = this.client,
      { startDate: rangeStart, endDate: rangeEnd, duration } = range;
    return Boolean(
      rangeStart &&
      (timeAxis.isContinuous || timeAxis.isTimeSpanInAxis(range)) &&
      DateHelper.intersectSpans(
        startDate,
        endDate,
        rangeStart,
        // Lines are included longer, to make sure label does not disappear
        duration
          ? rangeEnd
          : DateHelper.add(rangeStart, this._lineBufferDurationMS),
      ),
    );
  }
  getRangeDomConfig(timeRange, minDate, maxDate, relativeTo = 0) {
    const me = this,
      { client } = me,
      { rtl } = client,
      startPos =
        client.getCoordinateFromDate(
          DateHelper.max(timeRange.startDate, minDate),
          {
            respectExclusion: true,
          },
        ) - relativeTo,
      endPos = timeRange.endDate
        ? client.getCoordinateFromDate(
            DateHelper.min(timeRange.endDate, maxDate),
            {
              respectExclusion: true,
              isEnd: true,
            },
          ) - relativeTo
        : startPos,
      size = Math.abs(endPos - startPos),
      isRange = size > 0,
      translateX = rtl ? `calc(${startPos}px - 100%)` : `${startPos}px`;
    return {
      className: {
        [me.baseCls]: 1,
        [me.cls]: me.cls,
        [me.rangeCls]: isRange,
        [me.lineCls]: !isRange,
        [timeRange.cls]: timeRange.cls,
        "b-narrow-range": isRange && size < me.narrowThreshold,
        "b-readonly": timeRange.readOnly,
        "b-rtl": rtl,
      },
      dataset: {
        id: timeRange.id,
      },
      elementData: {
        timeRange,
      },
      style: client.isVertical
        ? `transform: translateY(${translateX}); ${isRange ? `height:${size}px` : ""};`
        : `transform: translateX(${translateX}); ${isRange ? `width:${size}px` : ""};`,
    };
  }
  renderRange(timeRange, startDate, endDate) {
    const me = this,
      { client } = me,
      { timeAxis } = client;
    if (
      me.shouldRenderRange(timeRange, startDate, endDate) &&
      timeAxis.startDate
    ) {
      const config = me.getRangeDomConfig(
          timeRange,
          timeAxis.startDate,
          timeAxis.endDate,
        ),
        icon =
          timeRange.iconCls &&
          StringHelper.xss`<i class="${timeRange.iconCls}"></i>`,
        name = timeRange.name && StringHelper.encodeHtml(timeRange.name),
        labelTpl =
          name || icon ? `${icon || ""}<label>${name || "&nbsp;"}</label>` : "",
        bodyConfig = {
          ...config,
          style: config.style + (timeRange.style || ""),
          html: me.bodyRenderer
            ? me.bodyRenderer({ timeRange })
            : me.showHeaderElements && !me.showLabelInBody
              ? ""
              : labelTpl,
        };
      let headerConfig;
      if (me.showHeaderElements) {
        headerConfig = {
          ...config,
          html: me.headerRenderer
            ? me.headerRenderer({ timeRange })
            : me.showLabelInBody
              ? ""
              : labelTpl,
        };
      }
      return { bodyConfig, headerConfig };
    }
  }
  // Cache label rotation to not have to calculate for each occurrence when using recurring timeranges
  cacheRotation(range, bodyElement) {
    if ((!range.iconCls && !range.name) || !range.duration) {
      return;
    }
    const label = bodyElement.firstElementChild;
    if (label && !range.recurringTimeSpan) {
      this._labelRotationMap[range.id] = this.client.isVertical
        ? label.offsetHeight < bodyElement.offsetHeight
        : label.offsetWidth > bodyElement.offsetWidth;
    }
  }
  applyRotation(range, bodyElement) {
    var _a4, _b, _c;
    const rotate =
      this._labelRotationMap[
        (_b = (_a4 = range.recurringTimeSpan) == null ? void 0 : _a4.id) != null
          ? _b
          : range.id
      ];
    (_c = bodyElement.firstElementChild) == null
      ? void 0
      : _c.classList.toggle("b-vertical", Boolean(rotate));
  }
  getBodyElementByRecord(idOrRecord) {
    const id =
      typeof idOrRecord === "string"
        ? idOrRecord
        : idOrRecord == null
          ? void 0
          : idOrRecord.id;
    return id != null && DomSync.getChild(this.bodyCanvas, id);
  }
  // Implement in subclasses
  resolveTimeRangeRecord(el) {}
  get headerContainerElement() {
    const me = this,
      { isVertical, timeView, timeAxisColumn } = me.client;
    if (!me._headerContainerElement) {
      if (isVertical && timeView.element) {
        me._headerContainerElement = timeView.element.parentElement;
      } else if (!isVertical) {
        me._headerContainerElement = timeAxisColumn.element;
      }
    }
    return me._headerContainerElement;
  }
  //endregion
  //region Settings
  get showHeaderElements() {
    return !this.client.hideHeaders && this._showHeaderElements;
  }
  updateShowHeaderElements(show) {
    const { client } = this;
    if (!this.isConfiguring) {
      client.element.classList.toggle(
        "b-sch-timeranges-with-headerelements",
        Boolean(show),
      );
      this.renderRanges();
    }
  }
  //endregion
  //region Menu items
  /**
   * Adds menu items for the context menu, and may mutate the menu configuration.
   * @param {Object} options Contains menu items and extra data retrieved from the menu target.
   * @param {Grid.column.Column} options.column Column for which the menu will be shown
   * @param {Object<String,MenuItemConfig|Boolean|null>} options.items A named object to describe menu items
   * @internal
   */
  populateTimeAxisHeaderMenu({ column, items: items2 }) {}
  //endregion
  //region Events & hooks
  onInternalPaint({ firstPaint }) {
    if (firstPaint && this.client.isHorizontal) {
      this.onUIReady();
    }
  }
  onSchedulerHorizontalScroll() {
    this.client.isHorizontal && this.renderRanges();
  }
  afterScroll() {
    this.client.isVertical && this.renderRanges();
  }
  updateLineBuffer() {
    const { timeAxisViewModel } = this.client;
    this._lineBufferDurationMS =
      timeAxisViewModel.getDateFromPosition(300) -
      timeAxisViewModel.getDateFromPosition(0);
  }
  onInternalResize(element, newWidth, newHeight, oldWidth, oldHeight) {
    if (this.client.isVertical && oldHeight !== newHeight) {
      this.renderRanges();
    }
  }
  onTimeAxisViewModelUpdate() {
    this.updateLineBuffer();
    this.refresh();
  }
  onTimeRangeClick(event) {
    const timeRangeRecord = this.resolveTimeRangeRecord(event.target);
    this.client.trigger(
      `timeRangeHeader${StringHelper.capitalize(event.type)}`,
      { event, domEvent: event, timeRangeRecord },
    );
  }
  //endregion
  //region Drag drop
  showTip(context) {
    const me = this;
    if (me.showTooltip) {
      me.clockTemplate = new ClockTemplate({
        scheduler: me.client,
      });
      me.tip = new Tooltip(
        ObjectHelper.assign(
          {
            id: `${me.client.id}-time-range-tip`,
            cls: "b-interaction-tooltip",
            align: "b-t",
            autoShow: true,
            updateContentOnMouseMove: true,
            forElement: context.element,
            getHtml: () => me.getTipHtml(context.record, context.element),
          },
          me.showTooltip,
        ),
      );
    }
  }
  destroyTip() {
    if (this.tip) {
      this.tip.destroy();
      this.tip = null;
    }
  }
  isElementDraggable(el) {
    el = el.closest(this.baseSelector + ":not(.b-resizing):not(.b-readonly)");
    return el && !el.classList.contains("b-over-resize-handle");
  }
  onDragStart({ context }) {
    const { client, drag } = this;
    if (client.isVertical) {
      drag.minY = 0;
      drag.maxY =
        client.timeAxisViewModel.totalSize - context.element.offsetHeight;
      drag.minX = 0;
      drag.maxX = Number.MAX_SAFE_INTEGER;
    } else {
      drag.minX = 0;
      drag.maxX =
        client.timeAxisViewModel.totalSize - context.element.offsetWidth;
      drag.minY = 0;
      drag.maxY = Number.MAX_SAFE_INTEGER;
    }
    client.element.classList.add("b-dragging-timerange");
  }
  onDrop({ context }) {
    this.client.element.classList.remove("b-dragging-timerange");
  }
  onInvalidDrop() {
    this.drag.reset();
    this.client.element.classList.remove("b-dragging-timerange");
    this.destroyTip();
  }
  updateDateIndicator({ startDate, endDate }) {
    const me = this,
      { tip } = me,
      endDateElement = tip.element.querySelector(".b-sch-tooltip-enddate");
    me.clockTemplate.updateDateIndicator(tip.element, startDate);
    endDateElement &&
      me.clockTemplate.updateDateIndicator(endDateElement, endDate);
  }
  onDrag({ context }) {
    const me = this,
      { client } = me,
      box = Rectangle.from(context.element),
      startPos = box.getStart(client.rtl, client.isHorizontal),
      endPos = box.getEnd(client.rtl, client.isHorizontal),
      startDate = client.getDateFromCoordinate(startPos, "round", false),
      endDate = client.getDateFromCoordinate(endPos, "round", false);
    me.updateDateIndicator({ startDate, endDate });
  }
  onDragReset() {}
  // endregion
  // region Resize
  onResizeStart() {
    var _a4;
    this.client.element.classList.add("b-resizing-timerange");
    (_a4 = this.hoverTooltip) == null ? void 0 : _a4.hide();
  }
  onResizeDrag() {}
  onResize() {}
  onInvalidResize() {}
  onResizeReset() {
    this.client.element.classList.remove("b-resizing-timerange");
  }
  //endregion
  //region Tooltip
  /**
   * Generates the html to display in the tooltip during drag drop.
   *
   */
  getTipHtml(record, element) {
    const me = this,
      { client } = me,
      box = Rectangle.from(element),
      startPos = box.getStart(client.rtl, client.isHorizontal),
      endPos = box.getEnd(client.rtl, client.isHorizontal),
      startDate = client.getDateFromCoordinate(startPos, "round", false),
      endDate =
        record.endDate && client.getDateFromCoordinate(endPos, "round", false),
      startText = client.getFormattedDate(startDate),
      endText = endDate && client.getFormattedEndDate(endDate, startDate);
    return me.dragTipTemplate({
      name: record.name || "",
      startDate,
      endDate,
      startText,
      endText,
      startClockHtml: me.clockTemplate.template({
        date: startDate,
        text: startText,
        cls: "b-sch-tooltip-startdate",
      }),
      endClockHtml:
        endText &&
        me.clockTemplate.template({
          date: endDate,
          text: endText,
          cls: "b-sch-tooltip-enddate",
        }),
    });
  }
  //endregion
};
__publicField(AbstractTimeRanges, "configurable", {
  /**
   * Set to `false` to not render range elements into the time axis header
   * @prp {Boolean}
   * @default
   * @category Common
   */
  showHeaderElements: true,
});
// Plugin configuration. This plugin chains some functions in Grid.
__publicField(AbstractTimeRanges, "pluginConfig", {
  chain: [
    "onInternalPaint",
    "populateTimeAxisHeaderMenu",
    "onSchedulerHorizontalScroll",
    "afterScroll",
    "onInternalResize",
  ],
});
AbstractTimeRanges._$name = "AbstractTimeRanges";

// ../Scheduler/lib/Scheduler/feature/ColumnLines.js
var emptyObject14 = Object.freeze({});
var ColumnLines = class extends InstancePlugin.mixin(
  AttachToProjectMixin_default,
  Delayable_default,
) {
  //region Config
  static get $name() {
    return "ColumnLines";
  }
  static get delayable() {
    return {
      refresh: {
        type: "raf",
        cancelOutstanding: true,
      },
    };
  }
  // Plugin configuration. This plugin chains some of the functions in Grid.
  static get pluginConfig() {
    return {
      after: [
        "render",
        "updateCanvasSize",
        "internalOnVisibleDateRangeChange",
        "onVisibleResourceRangeChange",
        "onVisibleResourceColumnChange",
      ],
    };
  }
  //endregion
  //region Init & destroy
  attachToResourceStore(resourceStore) {
    const { client } = this;
    super.attachToResourceStore(resourceStore);
    if (client.isVertical) {
      client.resourceStore.ion({
        name: "resourceStore",
        group({ groupers }) {
          if (groupers.length === 0) {
            this.refresh();
          }
        },
        thisObj: this,
      });
    }
  }
  doDisable(disable) {
    super.doDisable(disable);
    if (!this.isConfiguring) {
      this.refresh();
    }
  }
  //endregion
  //region Draw
  /**
   * Draw lines when scheduler/gantt is rendered.
   * @private
   */
  render() {
    this.refresh();
  }
  getColumnLinesDOMConfig(startDate, endDate) {
    var _a4;
    const me = this,
      { client } = me,
      { rtl } = client,
      m = rtl ? -1 : 1,
      { timeAxisViewModel, isHorizontal, resourceStore, variableColumnWidths } =
        client,
      { columnConfig } = timeAxisViewModel;
    const linesForLevel = timeAxisViewModel.columnLinesFor,
      majorLinesForLevel = Math.max(linesForLevel - 1, 0),
      start = startDate.getTime(),
      end = endDate.getTime(),
      domConfigs = [],
      dates = /* @__PURE__ */ new Set(),
      dimension = isHorizontal ? "X" : "Y";
    if (!me.disabled) {
      const addLineConfig = (tick, isMajor) => {
        const tickStart = tick.start.getTime();
        if (tickStart > start && tickStart < end && !dates.has(tickStart)) {
          dates.add(tickStart);
          domConfigs.push({
            role: "presentation",
            className: isMajor ? "b-column-line-major" : "b-column-line",
            style: {
              transform: `translate${dimension}(${tick.coord * m}px)`,
            },
            dataset: {
              line: isMajor ? `major-${tick.index}` : `line-${tick.index}`,
            },
          });
        }
      };
      if (linesForLevel !== majorLinesForLevel) {
        for (let i = 1; i <= columnConfig[majorLinesForLevel].length - 1; i++) {
          addLineConfig(columnConfig[majorLinesForLevel][i], true);
        }
      }
      for (let i = 1; i <= columnConfig[linesForLevel].length - 1; i++) {
        addLineConfig(columnConfig[linesForLevel][i], false);
      }
      if (!isHorizontal && client.columnLines) {
        const { columnWidth } = client.resourceColumns;
        let { first: firstResource, last: lastResource } =
          client.currentOrientation.getResourceRange(true);
        let nbrGroupHeaders = 0;
        if (firstResource > -1) {
          for (let i = firstResource; i < lastResource + 1; i++) {
            const resourceRecord = resourceStore.getAt(i);
            if (resourceRecord.isGroupHeader) {
              lastResource++;
              nbrGroupHeaders++;
              continue;
            }
            const instanceMeta = resourceRecord.instanceMeta(client),
              left = variableColumnWidths
                ? instanceMeta.insetStart +
                  client.getResourceWidth(resourceRecord) -
                  1
                : (i - nbrGroupHeaders + 1) * columnWidth - 1,
              groupParent =
                (_a4 = resourceRecord.groupParent) == null
                  ? void 0
                  : _a4.get(client.resourceStore.id);
            domConfigs.push({
              className: {
                "b-column-line": 1,
                "b-resource-column-line": 1,
                "b-resource-group-divider":
                  resourceStore.isGrouped &&
                  (groupParent == null
                    ? void 0
                    : groupParent.groupChildren[
                        (groupParent == null
                          ? void 0
                          : groupParent.groupChildren.length) - 1
                      ]) === resourceRecord,
              },
              style: {
                transform: `translateX(${left * m}px)`,
              },
              dataset: {
                line: `resource-${i}`,
              },
            });
          }
        }
      }
    }
    return domConfigs;
  }
  /**
   * Draw column lines that are in view
   * @private
   */
  refresh() {
    const me = this,
      { client } = me,
      { timeAxis } = client,
      { startDate, endDate } = client.visibleDateRange || emptyObject14,
      axisStart = timeAxis.startDate;
    if (!axisStart || !startDate || me.client.timeAxisSubGrid.collapsed) {
      return;
    }
    if (!me.element) {
      me.element = DomHelper.createElement({
        parent: client.timeAxisSubGridElement,
        className: "b-column-lines-canvas b-sch-canvas",
      });
    }
    const domConfigs = me.getColumnLinesDOMConfig(startDate, endDate);
    DomSync.sync({
      targetElement: me.element,
      domConfig: {
        onlyChildren: true,
        children: domConfigs,
        syncOptions: {
          // When zooming in and out we risk getting a lot of released lines if we do not limit it
          releaseThreshold: 4,
        },
      },
      syncIdField: "line",
    });
  }
  //endregion
  //region Events
  // Called when visible date range changes, for example from zooming, scrolling, resizing
  internalOnVisibleDateRangeChange() {
    this.refresh();
  }
  // Called when visible resource range changes, for example on scroll and resize
  onVisibleResourceRangeChange({ firstResource, lastResource }) {
    this.refresh();
  }
  onVisibleResourceColumnChange(width, oldWidth) {
    this.refresh();
  }
  updateCanvasSize() {
    this.refresh();
  }
  //endregion
};
ColumnLines._$name = "ColumnLines";
GridFeatureManager.registerFeature(ColumnLines, true, [
  "Scheduler",
  "Gantt",
  "TimelineHistogram",
]);

// ../Scheduler/lib/Scheduler/feature/mixin/DependencyCreation.js
var DependencyCreation_default = (Target) => {
  var _a4;
  return (
    (_a4 = class extends (Target || Base) {
      static get $name() {
        return "DependencyCreation";
      }
      static get defaultConfig() {
        return {
          /**
           * `false` to not show a tooltip while creating a dependency
           * @config {Boolean}
           * @default
           * @category Dependency creation
           */
          showCreationTooltip: true,
          /**
           * A tooltip config object that will be applied to the dependency creation {@link Core.widget.Tooltip}
           * @config {TooltipConfig}
           * @category Dependency creation
           */
          creationTooltip: null,
          /**
           * A template function that will be called to generate the HTML contents of the dependency creation tooltip.
           * You can return either an HTML string or a {@link DomConfig} object.
           * @prp {Function} creationTooltipTemplate
           * @param {Object} data Data about the dependency being created
           * @param {Scheduler.model.TimeSpan} data.source The from event
           * @param {Scheduler.model.TimeSpan} data.target The target event
           * @param {String} data.fromSide The from side (start, end, top, bottom)
           * @param {String} data.toSide The target side (start, end, top, bottom)
           * @param {Boolean} data.valid The validity of the dependency
           * @returns {String|DomConfig}
           * @category Dependency creation
           */
          /**
           * CSS class used for terminals
           * @config {String}
           * @default
           * @category Dependency terminals
           */
          terminalCls: "b-sch-terminal",
          /**
           * Where (on event bar edges) to display terminals. The sides are `'start'`, `'top'`,
           * `'end'` and `'bottom'`
           * @config {String[]}
           * @category Dependency terminals
           */
          terminalSides: ["start", "top", "end", "bottom"],
          /**
           * Set to `false` to not allow creating dependencies
           * @config {Boolean}
           * @default
           * @category Dependency creation
           */
          allowCreate: true,
        };
      }
      //endregion
      //region Init & destroy
      construct(client, config) {
        super.construct(client, config);
        const me = this;
        me.eventName = client.scheduledEventName;
        client.ion({ readOnly: () => me.updateCreateListeners() });
        me.updateCreateListeners();
        me.chain(client, "onElementTouchMove", "onElementTouchMove");
      }
      doDestroy() {
        var _a5, _b;
        const me = this;
        me.detachListeners("view");
        me.creationData = null;
        (_a5 = me.pointerUpMoveDetacher) == null ? void 0 : _a5.call(me);
        (_b = me.creationTooltip) == null ? void 0 : _b.destroy();
        super.doDestroy();
      }
      updateCreateListeners() {
        const me = this;
        if (!me.client) {
          return;
        }
        me.detachListeners("view");
        if (me.isCreateAllowed) {
          me.client.ion({
            name: "view",
            [`${me.eventName}MouseEnter`]: "onTimeSpanMouseEnter",
            [`${me.eventName}MouseLeave`]: "onTimeSpanMouseLeave",
            thisObj: me,
          });
        }
      }
      set allowCreate(value) {
        this._allowCreate = value;
        this.updateCreateListeners();
      }
      get allowCreate() {
        return this._allowCreate;
      }
      get isCreateAllowed() {
        return this.allowCreate && !this.client.readOnly && !this.disabled;
      }
      //endregion
      //region Terminal settings
      updateTerminalOffset(offset) {
        this.client.whenVisible(() => {
          this.client.foregroundCanvas.style.setProperty(
            "--scheduler-dependency-terminal-offset",
            `${-offset}px`,
          );
        });
      }
      updateTerminalSize(size) {
        if (typeof size === "number") {
          size = `${size}px`;
        }
        this.client.whenVisible(() => {
          this.client.foregroundCanvas.style.setProperty(
            "--scheduler-dependency-terminal-size",
            size ? `${size}` : null,
          );
        });
      }
      //endregion
      //region Events
      /**
       * Show terminals when mouse enters event/task element
       * @private
       */
      onTimeSpanMouseEnter({
        event,
        source,
        [`${this.eventName}Record`]: record,
        [`${this.eventName}Element`]: element,
        resourceRecord,
      }) {
        if (!record.isCreating && !record.readOnly) {
          const me = this,
            { creationData, client } = me,
            eventBarElement = DomHelper.down(
              element,
              source.eventInnerSelector,
            );
          if (
            record !== (creationData == null ? void 0 : creationData.source)
          ) {
            const { parent } = record;
            if (
              record.isEventModel &&
              parent &&
              !parent.isRoot &&
              client.eventStore.includes(parent)
            ) {
              const parentElement = client.getElementFromEventRecord(
                parent,
                resourceRecord,
                true,
              );
              parentElement && me.delayHideTerminals(parentElement);
            }
            me.delayShowTerminals(record, element);
            if (creationData && event.target.closest(client.eventSelector)) {
              creationData.timeSpanElement = eventBarElement;
              me.onOverTargetEventBar(event);
            }
          }
        }
      }
      /**
       * Hide terminals when mouse leaves event/task element
       * @private
       */
      onTimeSpanMouseLeave(event) {
        var _a5, _b, _c, _d, _e;
        const { eventRecord, event: domEvent } = event;
        if (!domEvent) {
          return;
        }
        const me = this,
          { creationData, client } = me,
          toEvent = (
            (_a5 = domEvent.relatedTarget) == null
              ? void 0
              : _a5.matches(".b-sch-terminal-hover-area, .b-sch-terminal")
          )
            ? null
            : (_b = domEvent.relatedTarget) == null
              ? void 0
              : _b.closest(client.eventSelector),
          toEventRecord =
            (_e =
              (_c = toEvent == null ? void 0 : toEvent.elementData) == null
                ? void 0
                : _c.eventRecord) != null
              ? _e
              : (_d = toEvent == null ? void 0 : toEvent.elementData) == null
                ? void 0
                : _d.taskRecord,
          { parent } = eventRecord != null ? eventRecord : {},
          element = event[`${me.eventName}Element`];
        if (domEvent.isTrusted || VersionHelper.isTestEnv || creationData) {
          me.delayHideTerminals(element);
        }
        if (parent && !parent.isRoot && client.eventStore.includes(parent)) {
          const parentElement = client.getElementFromEventRecord(parent);
          parentElement && me.delayShowTerminals(parent, parentElement);
        }
        if (creationData) {
          me.onOverNewTargetWhileCreating(
            domEvent.relatedTarget,
            !(toEventRecord == null ? void 0 : toEventRecord.readOnly) &&
              !(toEventRecord == null ? void 0 : toEventRecord.isOccurence)
              ? toEventRecord
              : null,
            domEvent,
          );
        }
      }
      onTerminalMouseOver(event) {
        this.clearTimeout(
          `hide-${event.target.closest(this.client.eventSelector).dataset.syncId}`,
        );
        if (this.creationData) {
          this.onOverTargetEventBar(event);
        }
      }
      /**
       * Remove hover styling when mouse leaves terminal. Also hides terminals when mouse leaves one it and not creating a
       * dependency.
       * @private
       */
      onTerminalMouseOut(event) {
        var _a5, _b, _c, _d;
        const me = this,
          { creationData, client } = me,
          fromEvent = event.target.closest(client.eventSelector),
          toEvent =
            (_a5 = event.relatedTarget) == null
              ? void 0
              : _a5.closest(client.eventSelector),
          toEventRecord =
            (_d =
              (_b = toEvent == null ? void 0 : toEvent.elementData) == null
                ? void 0
                : _b.eventRecord) != null
              ? _d
              : (_c = toEvent == null ? void 0 : toEvent.elementData) == null
                ? void 0
                : _c.taskRecord;
        if (
          toEvent !== fromEvent &&
          fromEvent &&
          !me.hasTimeout(`show-${fromEvent.dataset.syncId}`) &&
          (!creationData || fromEvent !== creationData.timeSpanElement)
        ) {
          me.delayHideTerminals(fromEvent);
          client.unhover(fromEvent, event);
        }
        if (creationData) {
          me.onOverNewTargetWhileCreating(
            event.relatedTarget,
            !(toEventRecord == null ? void 0 : toEventRecord.readOnly) &&
              !(toEventRecord == null ? void 0 : toEventRecord.isOccurence)
              ? toEventRecord
              : null,
            event,
          );
        }
      }
      /**
       * Start creating a dependency when mouse is pressed over terminal
       * @private
       */
      onTerminalPointerDown(event) {
        var _a5;
        const me = this;
        if (event.button === 0 && !me.creationData) {
          const { client } = me,
            timeAxisSubGridElement = client.timeAxisSubGridElement,
            terminalNode = event.target,
            timeSpanElement = terminalNode.closest(client.eventInnerSelector),
            viewBounds = Rectangle.from(client.element, document.body);
          event.stopPropagation();
          me.creationData = {
            sourceElement: timeSpanElement,
            source: client.resolveTimeSpanRecord(timeSpanElement).$original,
            fromSide: terminalNode.dataset.side,
            startPoint: Rectangle.from(terminalNode, timeAxisSubGridElement)
              .center,
            startX: event.pageX - viewBounds.x + client.scrollLeft,
            startY: event.pageY - viewBounds.y + client.scrollTop,
            valid: false,
            sourceResource:
              (_a5 = client.resolveResourceRecord) == null
                ? void 0
                : _a5.call(client, event),
            tooltip: me.creationTooltip,
          };
          me.pointerUpMoveDetacher = EventHelper.on({
            pointerup: {
              element: client.element.getRootNode(),
              handler: "onMouseUp",
              passive: false,
            },
            pointermove: {
              element: timeAxisSubGridElement,
              handler: "onMouseMove",
              passive: false,
            },
            thisObj: me,
          });
          me.documentPointerUpDetacher = EventHelper.on({
            pointerup: {
              element: document,
              handler: "onDocumentMouseUp",
            },
            keydown: {
              element: document,
              handler: ({ key }) => {
                if (key === "Escape") {
                  me.abort();
                }
              },
            },
            thisObj: me,
          });
        }
      }
      onElementTouchMove(event) {
        var _a5;
        (_a5 = super.onElementTouchMove) == null
          ? void 0
          : _a5.call(this, event);
        if (this.connector) {
          event.preventDefault();
        }
      }
      /**
       * Update connector line showing dependency between source and target when mouse moves. Also check if mouse is over
       * a valid target terminal
       * @private
       */
      onMouseMove(event) {
        const me = this,
          { client, creationData: data } = me,
          viewBounds = Rectangle.from(client.element, document.body),
          deltaX = event.pageX - viewBounds.x + client.scrollLeft - data.startX,
          deltaY = event.pageY - viewBounds.y + client.scrollTop - data.startY,
          length = Math.round(Math.sqrt(deltaX * deltaX + deltaY * deltaY)) - 3,
          angle = Math.atan2(deltaY, deltaX);
        let { connector } = me;
        if (!connector) {
          if (me.onRequestDragCreate(event) === false) {
            return;
          }
          connector = me.connector;
        }
        connector.style.width = `${length}px`;
        connector.style.transform = `rotate(${angle}rad)`;
        me.lastMouseMoveEvent = event;
      }
      onRequestDragCreate(event) {
        const me = this,
          { client, creationData: data } = me;
        if (
          client.trigger("beforeDependencyCreateDrag", {
            data,
            source: data.source,
          }) === false
        ) {
          me.abort();
          return false;
        }
        client.element.classList.add("b-creating-dependency");
        me.createConnector(data.startPoint.x, data.startPoint.y);
        client.trigger("dependencyCreateDragStart", {
          data,
          source: data.source,
        });
        if (me.showCreationTooltip) {
          const tip =
            me.creationTooltip || (me.creationTooltip = me.createDragTooltip());
          me.creationData.tooltip = tip;
          tip.disabled = false;
          tip.show();
          tip.onMouseMove(event);
        }
        client.scrollManager.startMonitoring({
          scrollables: [
            {
              element: client.timeAxisSubGrid.scrollable.element,
              direction: "horizontal",
            },
            {
              element: client.scrollable.element,
              direction: "vertical",
            },
          ],
          callback: () =>
            me.lastMouseMoveEvent && me.onMouseMove(me.lastMouseMoveEvent),
        });
      }
      onOverTargetEventBar(event) {
        const me = this,
          { client, creationData: data, allowDropOnEventBar } = me,
          { target } = event;
        let overEventRecord = client.resolveTimeSpanRecord(target).$original;
        if (overEventRecord == null ? void 0 : overEventRecord.isEventSegment) {
          overEventRecord = overEventRecord.event;
        }
        if (
          Objects.isPromise(data.valid) ||
          (!allowDropOnEventBar && !target.classList.contains(me.terminalCls))
        ) {
          return;
        }
        if (overEventRecord !== data.source) {
          me.onOverNewTargetWhileCreating(target, overEventRecord, event);
        }
      }
      async onOverNewTargetWhileCreating(
        targetElement,
        overEventRecord,
        event,
      ) {
        var _a5, _b;
        const me = this,
          { client, creationData: data, allowDropOnEventBar, connector } = me;
        if (Objects.isPromise(data.valid)) {
          return;
        }
        if (data.finalizing) {
          return;
        }
        if (!connector) {
          return;
        }
        connector.classList.remove("b-valid", "b-invalid");
        data.timeSpanElement &&
          DomHelper.removeClsGlobally(
            data.timeSpanElement,
            "b-sch-terminal-active",
          );
        if (
          !overEventRecord ||
          overEventRecord === data.source ||
          (!allowDropOnEventBar &&
            !targetElement.classList.contains(me.terminalCls))
        ) {
          data.target = data.toSide = null;
          data.valid = false;
          connector.classList.add("b-invalid");
        } else {
          const target = (data.target = overEventRecord),
            { source } = data;
          let toSide = targetElement.dataset.side;
          if (
            allowDropOnEventBar &&
            !targetElement.classList.contains(me.terminalCls)
          ) {
            toSide = me.getTargetSideFromType(
              me.dependencyStore.modelClass.fieldMap.type.defaultValue ||
                DependencyBaseModel.Type.EndToStart,
            );
          }
          if (client.resolveResourceRecord) {
            data.targetResource = client.resolveResourceRecord(event);
          }
          let dependencyType;
          data.toSide = toSide;
          const fromSide = data.fromSide,
            updateValidity = (valid2) => {
              if (!me.isDestroyed) {
                data.valid = valid2;
                targetElement.classList.add(valid2 ? "b-valid" : "b-invalid");
                connector.classList.add(valid2 ? "b-valid" : "b-invalid");
                client.trigger("dependencyValidationComplete", {
                  data,
                  source,
                  target,
                  dependencyType,
                });
              }
            };
          switch (true) {
            case fromSide === "start" && toSide === "start":
              dependencyType = DependencyBaseModel.Type.StartToStart;
              break;
            case fromSide === "start" && toSide === "end":
              dependencyType = DependencyBaseModel.Type.StartToEnd;
              break;
            case fromSide === "end" && toSide === "start":
              dependencyType = DependencyBaseModel.Type.EndToStart;
              break;
            case fromSide === "end" && toSide === "end":
              dependencyType = DependencyBaseModel.Type.EndToEnd;
              break;
          }
          client.trigger("dependencyValidationStart", {
            data,
            source,
            target,
            dependencyType,
          });
          let valid = (data.valid = me.dependencyStore.isValidDependency(
            source,
            target,
            dependencyType,
          ));
          if (Objects.isPromise(valid)) {
            valid = await valid;
            updateValidity(valid);
          } else {
            updateValidity(valid);
          }
          const validityCls = valid ? "b-valid" : "b-invalid";
          connector.classList.add(validityCls);
          (_b =
            (_a5 = data.timeSpanElement) == null
              ? void 0
              : _a5.querySelector(`.${me.terminalCls}[data-side=${toSide}]`)) ==
          null
            ? void 0
            : _b.classList.add("b-sch-terminal-active", validityCls);
        }
        me.updateCreationTooltip();
      }
      /**
       * Create a new dependency if mouse release over valid terminal. Hides connector
       * @private
       */
      async onMouseUp() {
        var _a5;
        const me = this,
          data = me.creationData;
        data.finalizing = true;
        (_a5 = me.pointerUpMoveDetacher) == null ? void 0 : _a5.call(me);
        if (data.valid) {
          const result = await me.client.trigger(
            "beforeDependencyCreateFinalize",
            data,
          );
          if (result === false) {
            data.valid = false;
          } else if (Objects.isPromise(data.valid)) {
            data.valid = await data.valid;
          }
          if (data.valid) {
            let dependency = await me.createDependency(data);
            if (dependency !== null) {
              if (Objects.isPromise(dependency)) {
                dependency = await dependency;
              }
              data.dependency = dependency;
              me.client.trigger("dependencyCreateDrop", {
                data,
                source: data.source,
                target: data.target,
                dependency,
              });
              await me.doAfterDependencyDrop(data);
            }
          } else {
            await me.doAfterDependencyDrop(data);
          }
        } else {
          data.valid = false;
          await me.doAfterDependencyDrop(data);
        }
        me.abort();
      }
      doAfterDependencyDrop(data) {
        this.client.trigger("afterDependencyCreateDrop", {
          data,
          ...data,
        });
      }
      onDocumentMouseUp({ target }) {
        if (!this.client.timeAxisSubGridElement.contains(target)) {
          this.abort();
        }
      }
      /**
       * Aborts dependency creation, removes proxy and cleans up listeners
       * @category Dependency creation
       */
      abort() {
        var _a5, _b;
        const me = this,
          { client, creationData } = me;
        if (creationData) {
          const { source, sourceResource, target, targetResource } =
            creationData;
          if (source) {
            const el = client.getElementFromEventRecord(source, sourceResource);
            if (el) {
              me.hideTerminals(el);
            }
          }
          if (target) {
            const el = client.getElementFromEventRecord(target, targetResource);
            if (el) {
              me.hideTerminals(el);
            }
          }
        }
        if (me.creationTooltip) {
          me.creationTooltip.disabled = true;
        }
        me.creationData = me.lastMouseMoveEvent = null;
        (_a5 = me.pointerUpMoveDetacher) == null ? void 0 : _a5.call(me);
        (_b = me.documentPointerUpDetacher) == null ? void 0 : _b.call(me);
        me.removeConnector();
      }
      //endregion
      //region Connector
      /**
       * Creates a connector line that visualizes dependency source & target
       * @private
       */
      createConnector(x, y) {
        const me = this,
          { client } = me;
        me.clearTimeout(me.removeConnectorTimeout);
        me.connector = DomHelper.createElement({
          parent: client.timeAxisSubGridElement,
          className: `${me.baseCls}-connector`,
          style: `left:${x}px;top:${y}px`,
        });
        client.element.classList.add("b-creating-dependency");
      }
      createDragTooltip() {
        const me = this,
          { client } = me;
        return (me.creationTooltip = Tooltip.new(
          {
            id: `${client.id}-dependency-drag-tip`,
            cls: "b-sch-dependency-creation-tooltip",
            loadingMsg: "",
            anchorToTarget: false,
            // Keep tip visible until drag drop operation is finalized
            forElement: client.timeAxisSubGridElement,
            trackMouse: true,
            // Do not constrain at all, want it to be able to go outside of the viewport to not get in the way
            constrainTo: null,
            header: {
              dock: "right",
            },
            internalListeners: {
              // Show initial content immediately
              beforeShow: "updateCreationTooltip",
              thisObj: me,
            },
          },
          me.creationTooltip,
        ));
      }
      /**
       * Remove connector
       * @private
       */
      removeConnector() {
        const me = this,
          { connector, client } = me;
        if (connector) {
          connector.classList.add("b-removing");
          connector.style.width = "0";
          me.removeConnectorTimeout = me.setTimeout(() => {
            connector.remove();
            me.connector = null;
          }, 200);
        }
        client.element.classList.remove("b-creating-dependency");
        me.creationTooltip && me.creationTooltip.hide();
        client.scrollManager.stopMonitoring();
      }
      //endregion
      //region Terminals
      delayShowTerminals(timeSpanRecord, element) {
        const me = this,
          { syncId } = element.dataset;
        me.clearTimeout(`hide-${syncId}`);
        me.clearTimeout(`show-${syncId}`);
        element.classList.remove("b-hiding-terminals");
        if (!me.terminalShowDelay) {
          me.showTerminals(timeSpanRecord, element);
        } else {
          me.setTimeout({
            fn: () => me.showTerminals(timeSpanRecord, element),
            name: `show-${syncId}`,
            args: [timeSpanRecord, element],
            delay: me.terminalShowDelay,
          });
        }
      }
      delayHideTerminals(element) {
        const me = this,
          { syncId } = element.dataset;
        me.clearTimeout(`hide-${syncId}`);
        me.clearTimeout(`show-${syncId}`);
        element.classList.add("b-hiding-terminals");
        if (!me.terminalHideDelay) {
          me.hideTerminals(element);
        } else {
          me.setTimeout({
            fn: () => me.hideTerminals(element),
            name: `hide-${syncId}`,
            args: [element],
            delay: me.terminalHideDelay,
          });
        }
      }
      /**
       * Show terminals for specified event at sides defined in #terminalSides.
       * @param {Scheduler.model.TimeSpan} timeSpanRecord Event/task to show terminals for
       * @param {HTMLElement} [element] Event/task element, defaults to using the first element found for the task
       * @category Dependency creation
       */
      showTerminals(
        timeSpanRecord,
        element = this.client.getElementFromEventRecord(timeSpanRecord),
      ) {
        const me = this;
        if (!me.isCreateAllowed || !timeSpanRecord.project || !element) {
          return;
        }
        const { client } = me,
          cls2 = me.terminalCls,
          terminalsVisibleCls = `${cls2}s-visible`;
        if (me.showingTerminalsFor) {
          me.hideTerminals(me.showingTerminalsFor);
        }
        element = DomHelper.down(element, me.client.eventInnerSelector);
        if (
          !element.classList.contains(terminalsVisibleCls) &&
          !client.element.classList.contains("b-resizing-event") &&
          !client.readOnly
        ) {
          if (
            client.trigger("beforeShowTerminals", {
              source: timeSpanRecord,
            }) === false
          ) {
            return;
          }
          DomHelper.createElement({
            parent: element.closest(client.eventSelector),
            className: "b-sch-terminal-hover-area",
          });
          me.terminalSides.forEach((side) => {
            side = me.fixSide(side);
            const terminal = DomHelper.createElement({
              parent: element,
              className: `${cls2} ${cls2}-${side}`,
              dataset: {
                side,
                feature: true,
              },
            });
            terminal.detacher = EventHelper.on({
              element: terminal,
              mouseover: "onTerminalMouseOver",
              mouseout: "onTerminalMouseOut",
              // Needs to be pointerdown to match DragHelper, otherwise will be preventing wrong event
              pointerdown: {
                handler: "onTerminalPointerDown",
                capture: true,
              },
              thisObj: me,
            });
          });
          element.classList.add(terminalsVisibleCls);
          timeSpanRecord.internalCls.add(terminalsVisibleCls);
        }
      }
      fixSide(side) {
        if (side === "left") {
          return "start";
        }
        if (side === "right") {
          return "end";
        }
        return side;
      }
      /**
       * Hide terminals for specified event
       * @param {HTMLElement} eventElement Event element
       * @category Dependency creation
       */
      hideTerminals(eventElement) {
        var _a5;
        const me = this,
          { client } = me,
          eventParams = client.getTimeSpanMouseEventParams(eventElement),
          timeSpanRecord =
            eventParams == null ? void 0 : eventParams[`${me.eventName}Record`],
          terminalsVisibleCls = `${me.terminalCls}s-visible`;
        (_a5 = eventElement.querySelector(".b-sch-terminal-hover-area")) == null
          ? void 0
          : _a5.remove();
        DomHelper.forEachSelector(
          eventElement,
          `> ${client.eventInnerSelector} > .${me.terminalCls}`,
          (terminal) => {
            var _a6;
            (_a6 = terminal.detacher) == null ? void 0 : _a6.call(terminal);
            terminal.remove();
          },
        );
        DomHelper.down(
          eventElement,
          client.eventInnerSelector,
        ).classList.remove(terminalsVisibleCls);
        timeSpanRecord == null
          ? void 0
          : timeSpanRecord.internalCls.remove(terminalsVisibleCls);
        eventElement.classList.remove("b-hiding-terminals");
      }
      //endregion
      //region Dependency creation
      /**
       * Create a new dependency from source terminal to target terminal
       * @internal
       */
      createDependency(data) {
        const { source, target, fromSide, toSide } = data,
          type = (fromSide === "start" ? 0 : 2) + (toSide === "end" ? 1 : 0);
        const newDependency = this.dependencyStore.add({
          from: source.id,
          to: target.id,
          type,
          fromSide,
          toSide,
        });
        return newDependency !== null ? newDependency[0] : null;
      }
      getTargetSideFromType(type) {
        if (
          type === DependencyBaseModel.Type.StartToStart ||
          type === DependencyBaseModel.Type.EndToStart
        ) {
          return "start";
        }
        return "end";
      }
      //endregion
      //region Tooltip
      /**
       * Update dependency creation tooltip
       * @private
       */
      updateCreationTooltip() {
        const me = this;
        if (!me.showCreationTooltip) {
          return;
        }
        const data = me.creationData,
          { valid } = data,
          tip = me.creationTooltip,
          { classList } = tip.element;
        if (Objects.isPromise(valid)) {
          classList.remove("b-invalid");
          classList.add("b-checking");
          return new Promise((resolve) =>
            valid.then((valid2) => {
              data.valid = valid2;
              if (!tip.isDestroyed) {
                resolve(me.updateCreationTooltip());
              }
            }),
          );
        }
        tip.html = me.creationTooltipTemplate(data);
      }
      creationTooltipTemplate(data) {
        var _a5, _b;
        const me = this,
          { tooltip, valid } = data,
          { classList } = tooltip.element;
        Object.assign(data, {
          fromText: StringHelper.encodeHtml(data.source.name),
          toText: StringHelper.encodeHtml(
            (_b = (_a5 = data.target) == null ? void 0 : _a5.name) != null
              ? _b
              : "",
          ),
          fromSide: data.fromSide,
          toSide: data.toSide || "",
        });
        let tipTitleIconClsSuffix, tipTitleText;
        classList.toggle("b-invalid", !valid);
        classList.remove("b-checking");
        if (valid === true) {
          tipTitleIconClsSuffix = "valid";
          tipTitleText = me.L("L{Dependencies.valid}");
        } else {
          tipTitleIconClsSuffix = "invalid";
          tipTitleText = me.L("L{Dependencies.invalid}");
        }
        tooltip.title = `<i class="b-icon b-icon-${tipTitleIconClsSuffix}"></i>${tipTitleText}`;
        return {
          children: [
            {
              className: "b-sch-dependency-tooltip",
              children: [
                {
                  dataset: { ref: "fromLabel" },
                  tag: "label",
                  text: me.L("L{Dependencies.from}"),
                },
                { dataset: { ref: "fromText" }, text: data.fromText },
                {
                  dataset: { ref: "fromBox" },
                  className: `b-sch-box b-${data.fromSide}`,
                },
                {
                  dataset: { ref: "toLabel" },
                  tag: "label",
                  text: me.L("L{Dependencies.to}"),
                },
                { dataset: { ref: "toText" }, text: data.toText },
                {
                  dataset: { ref: "toBox" },
                  className: `b-sch-box b-${data.toSide}`,
                },
              ],
            },
          ],
        };
      }
      //endregion
      doDisable(disable) {
        if (!this.isConfiguring) {
          this.updateCreateListeners();
        }
        super.doDisable(disable);
      }
    }), //region Config
    __publicField(_a4, "configurable", {
      /**
       * `false` to require a drop on a target event bar side circle to define the dependency type.
       * If dropped on the event bar, the `defaultValue` of the DependencyModel `type` field will be used to
       * determine the target task side.
       *
       * @prp {Boolean}
       * @default
       * @category Dependency creation
       */
      allowDropOnEventBar: true,
      /**
       * Terminal diameter in px, overrides the default CSS value for it (which might depend on theme).
       *
       * {@note}
       * Use an even number to avoid cropped terminals.
       * {/@note}
       *
       * Also accepts a string value representing a CSS size, e.g. '1.5em'.
       *
       * @prp {Number|String}
       * @category Dependency terminals
       */
      terminalSize: null,
      /**
       * Terminal offset from their initial position, in px. Positive values move terminals further away from the
       * event bar, negative values inside the event bar.
       *
       * @prp {Number}
       * @default 0
       * @category Dependency terminals
       */
      terminalOffset: null,
      /**
       * Delay in ms before showing the terminals when hovering over an event bar.
       *
       * Can be used for a more "stable" UI, where the terminals are not shown immediately when hovering over an event
       * bar and thus have fewer things moving when mouse is moved quickly over multiple event bars.
       *
       * @prp {Number}
       * @default 0
       * @category Dependency terminals
       */
      terminalShowDelay: 0,
      /**
       * Delay in ms before hiding the terminals when the mouse leaves an event bar or terminal.
       *
       * Can be used to make the UI more forgiving, accidentally leaving the event bar or terminal will not
       * immediately hide the terminals.
       *
       * Can also be used to play a hide animation, set a `terminalHideDelay` that is longer than your animation's
       * duration. The `b-hiding-terminals` CSS class is added to the event wrapper while the terminals are being
       * hidden.
       *
       * @prp {Number}
       * @default 0
       * @category Dependency terminals
       */
      terminalHideDelay: 0,
    }),
    _a4
  );
};

// ../Scheduler/lib/Scheduler/feature/mixin/DependencyGridCache.js
var ROWS_PER_CELL = 25;
var DependencyGridCache_default = (Target) => {
  var _a4;
  return (
    (_a4 = class extends Target {
      constructor() {
        super(...arguments);
        __publicField(this, "gridCache", null);
      }
      // Dependencies that might intersect the current viewport and thus should be considered for drawing
      getDependenciesToConsider(startMS, endMS, startIndex, endIndex) {
        const me = this,
          { gridCache } = me,
          { timeAxis } = me.client;
        if (gridCache) {
          const dependencies = /* @__PURE__ */ new Set(),
            fromMSCell = Math.floor(
              (startMS - timeAxis.startMS) / me.MS_PER_CELL,
            ),
            toMSCell = Math.floor((endMS - timeAxis.startMS) / me.MS_PER_CELL),
            fromRowCell = Math.floor(startIndex / ROWS_PER_CELL),
            toRowCell = Math.floor(endIndex / ROWS_PER_CELL);
          for (let i = fromMSCell; i <= toMSCell; i++) {
            const msCell = gridCache[i];
            if (msCell) {
              for (let j = fromRowCell; j <= toRowCell; j++) {
                const intersectingDependencies = msCell[j];
                if (intersectingDependencies) {
                  for (let i2 = 0; i2 < intersectingDependencies.length; i2++) {
                    dependencies.add(intersectingDependencies[i2]);
                  }
                }
              }
            }
          }
          return dependencies;
        }
      }
      // A (single) dependency was drawn, we might want to store info about it in the grid cache
      afterDrawDependency(
        dependency,
        fromIndex,
        toIndex,
        fromDateMS,
        toDateMS,
      ) {
        var _a5, _b;
        const me = this;
        if (me.constructGridCache) {
          const { MS_PER_CELL } = me,
            { startMS: timeAxisStartMS, endMS: timeAxisEndMS } =
              me.client.timeAxis,
            timeAxisCells = Math.ceil(
              (timeAxisEndMS - timeAxisStartMS) / MS_PER_CELL,
            ),
            fromMSCell = Math.floor(
              (fromDateMS - timeAxisStartMS) / MS_PER_CELL,
            ),
            toMSCell = Math.floor((toDateMS - timeAxisStartMS) / MS_PER_CELL),
            fromRowCell = Math.floor(fromIndex / ROWS_PER_CELL),
            toRowCell = Math.floor(toIndex / ROWS_PER_CELL),
            firstMSCell = Math.min(fromMSCell, toMSCell),
            lastMSCell = Math.max(fromMSCell, toMSCell),
            firstRowCell = Math.min(fromRowCell, toRowCell),
            lastRowCell = Math.max(fromRowCell, toRowCell);
          if (
            (firstMSCell < 0 && lastMSCell < 0) ||
            (firstMSCell > timeAxisCells && lastMSCell > timeAxisCells)
          ) {
            return;
          }
          const startMSCell = Math.max(firstMSCell, 0),
            endMSCell = Math.min(lastMSCell, timeAxisCells);
          for (let i = startMSCell; i <= endMSCell; i++) {
            const msCell =
              (_a5 = me.gridCache[i]) != null ? _a5 : (me.gridCache[i] = {});
            for (let j = firstRowCell; j <= lastRowCell; j++) {
              const rowCell = (_b = msCell[j]) != null ? _b : (msCell[j] = []);
              rowCell.push(dependency);
            }
          }
        }
      }
      // All dependencies are about to be drawn, check if we need to build the grid cache
      beforeDraw() {
        const me = this;
        if (!me.gridCache) {
          const { visibleDateRange } = me.client;
          me.constructGridCache = true;
          me.MS_PER_CELL = Math.max(
            visibleDateRange.endMS - visibleDateRange.startMS,
            1e3,
          );
          me.gridCache = {};
        }
      }
      // All dependencies are drawn, we no longer need to rebuild the cache
      afterDraw() {
        this.constructGridCache = false;
      }
      reset() {
        this.gridCache = null;
      }
    }),
    __publicField(_a4, "$name", "DependencyGridCache"),
    _a4
  );
};

// ../Scheduler/lib/Scheduler/util/RectangularPathFinder.js
var THRESHOLD = Math.min(1 / globalThis.devicePixelRatio, 0.75);
var BOX_PROPERTIES = ["start", "end", "top", "bottom"];
var equalEnough = (a, b) => Math.abs(a - b) < 0.1;
var sideToSide = {
  l: "left",
  r: "right",
  t: "top",
  b: "bottom",
};
var RectangularPathFinder = class _RectangularPathFinder extends Base {
  static get configurable() {
    return {
      /**
       * Default start connection side: 'left', 'right', 'top', 'bottom'
       * @config {'top'|'bottom'|'left'|'right'}
       * @default
       */
      startSide: "right",
      // /**
      //  * Default start arrow size in pixels
      //  * @config {Number}
      //  * @default
      //  */
      // startArrowSize : 0,
      /**
       * Default start arrow staff size in pixels
       * @config {Number}
       * @default
       */
      startArrowMargin: 12,
      /**
       * Default starting connection point shift from box's arrow pointing side middle point
       * @config {Number}
       * @default
       */
      startShift: 0,
      /**
       * Default end arrow pointing direction, possible values are: 'left', 'right', 'top', 'bottom'
       * @config {'top'|'bottom'|'left'|'right'}
       * @default
       */
      endSide: "left",
      // /**
      //  * Default end arrow size in pixels
      //  * @config {Number}
      //  * @default
      //  */
      // endArrowSize : 0,
      /**
       * Default end arrow staff size in pixels
       * @config {Number}
       * @default
       */
      endArrowMargin: 12,
      /**
       * Default ending connection point shift from box's arrow pointing side middle point
       * @config {Number}
       * @default
       */
      endShift: 0,
      /**
       * Start / End box vertical margin, the amount of pixels from top and bottom line of a box where drawing
       * is prohibited
       * @config {Number}
       * @default
       */
      verticalMargin: 2,
      /**
       * Start / End box horizontal margin, the amount of pixels from left and right line of a box where drawing
       * @config {Number}
       * @default
       */
      horizontalMargin: 5,
      /**
       * Other rectangular areas (obstacles) to search path through
       * @config {Object[]}
       * @default
       */
      otherBoxes: null,
      /**
       * The owning Scheduler. Mandatory so that it can determin RTL state.
       * @config {Scheduler.view.Scheduler}
       * @private
       */
      client: {},
    };
  }
  /**
   * Returns list of horizontal and vertical segments connecting two boxes
   * <pre>
   *    |    | |  |    |       |
   *  --+----+----+----*-------*---
   *  --+=>Start  +----*-------*--
   *  --+----+----+----*-------*--
   *    |    | |  |    |       |
   *    |    | |  |    |       |
   *  --*----*-+-------+-------+--
   *  --*----*-+         End <=+--
   *  --*----*-+-------+-------+--
   *    |    | |  |    |       |
   * </pre>
   * Path goes by lines (-=) and turns at intersections (+), boxes depicted are adjusted by horizontal/vertical
   * margin and arrow margin, original boxes are smaller (path can't go at original box borders). Algorithm finds
   * the shortest path with minimum amount of turns. In short it's mix of "Lee" and "Dijkstra pathfinding"
   * with turns amount taken into account for distance calculation.
   *
   * The algorithm is not very performant though, it's O(N^2), where N is amount of
   * points in the grid, but since the maximum amount of points in the grid might be up to 34 (not 36 since
   * two box middle points are not permitted) that might be ok for now.
   *
   * @param {Object} lineDef An object containing any of the class configuration option overrides as well
   *                         as `startBox`, `endBox`, `startHorizontalMargin`, `startVerticalMargin`,
   *                         `endHorizontalMargin`, `endVerticalMargin` properties
   * @param {Object} lineDef.startBox An object containing `start`, `end`, `top`, `bottom` properties
   * @param {Object} lineDef.endBox   An object containing `start`, `end`, `top`, `bottom` properties
   * @param {Number} lineDef.startHorizontalMargin Horizontal margin override for start box
   * @param {Number} lineDef.startVerticalMargin   Vertical margin override for start box
   * @param {Number} lineDef.endHorizontalMargin   Horizontal margin override for end box
   * @param {Number} lineDef.endVerticalMargin     Vertical margin override for end box
   *
   *
   * @returns {Object[]|Boolean} Array of line segments or false if path cannot be found
   * @returns {Number} return.x1
   * @returns {Number} return.y1
   * @returns {Number} return.x2
   * @returns {Number} return.y2
   */
  //
  //@ignore
  //@privateparam {Function[]|Function} noPathFallbackFn
  //     A function or array of functions which will be tried in case a path can't be found
  //     Each function will be given a line definition it might try to adjust somehow and return.
  //     The new line definition returned will be tried to find a path.
  //     If a function returns false, then next function will be called if any.
  //
  findPath(lineDef, noPathFallbackFn) {
    const me = this,
      originalLineDef = lineDef;
    let lineDefFull,
      startBox,
      endBox,
      startShift,
      endShift,
      startSide,
      endSide,
      startArrowMargin,
      endArrowMargin,
      horizontalMargin,
      verticalMargin,
      startHorizontalMargin,
      startVerticalMargin,
      endHorizontalMargin,
      endVerticalMargin,
      otherHorizontalMargin,
      otherVerticalMargin,
      otherBoxes,
      connStartPoint,
      connEndPoint,
      pathStartPoint,
      pathEndPoint,
      gridStartPoint,
      gridEndPoint,
      startGridBox,
      endGridBox,
      grid,
      path,
      tryNum;
    noPathFallbackFn = ArrayHelper.asArray(noPathFallbackFn);
    for (tryNum = 0; lineDef && !path; ) {
      lineDefFull = Object.assign(me.config, lineDef);
      startBox = lineDefFull.startBox;
      endBox = lineDefFull.endBox;
      startShift = lineDefFull.startShift;
      endShift = lineDefFull.endShift;
      startSide = lineDefFull.startSide;
      endSide = lineDefFull.endSide;
      startArrowMargin = lineDefFull.startArrowMargin;
      endArrowMargin = lineDefFull.endArrowMargin;
      horizontalMargin = lineDefFull.horizontalMargin;
      verticalMargin = lineDefFull.verticalMargin;
      startHorizontalMargin = lineDefFull.hasOwnProperty(
        "startHorizontalMargin",
      )
        ? lineDefFull.startHorizontalMargin
        : horizontalMargin;
      startVerticalMargin = lineDefFull.hasOwnProperty("startVerticalMargin")
        ? lineDefFull.startVerticalMargin
        : verticalMargin;
      endHorizontalMargin = lineDefFull.hasOwnProperty("endHorizontalMargin")
        ? lineDefFull.endHorizontalMargin
        : horizontalMargin;
      endVerticalMargin = lineDefFull.hasOwnProperty("endVerticalMargin")
        ? lineDefFull.endVerticalMargin
        : verticalMargin;
      otherHorizontalMargin = lineDefFull.hasOwnProperty(
        "otherHorizontalMargin",
      )
        ? lineDefFull.otherHorizontalMargin
        : horizontalMargin;
      otherVerticalMargin = lineDefFull.hasOwnProperty("otherVerticalMargin")
        ? lineDefFull.otherVerticalMargin
        : verticalMargin;
      otherBoxes = lineDefFull.otherBoxes;
      startSide = me.normalizeSide(startSide);
      endSide = me.normalizeSide(endSide);
      connStartPoint = me.getConnectionCoordinatesFromBoxSideShift(
        startBox,
        startSide,
        startShift,
      );
      connEndPoint = me.getConnectionCoordinatesFromBoxSideShift(
        endBox,
        endSide,
        endShift,
      );
      startGridBox = me.calcGridBaseBoxFromBoxAndDrawParams(
        startBox,
        startSide,
        startArrowMargin,
        startHorizontalMargin,
        startVerticalMargin,
      );
      endGridBox = me.calcGridBaseBoxFromBoxAndDrawParams(
        endBox,
        endSide,
        endArrowMargin,
        endHorizontalMargin,
        endVerticalMargin,
      );
      BOX_PROPERTIES.forEach((property) => {
        if (
          Math.abs(startGridBox[property] - endGridBox[property]) <= THRESHOLD
        ) {
          endGridBox[property] = startGridBox[property];
        }
      });
      if (me.shouldLookForPath(startBox, endBox, startGridBox, endGridBox)) {
        otherBoxes =
          otherBoxes == null
            ? void 0
            : otherBoxes.map((box) =>
                me.calcGridBaseBoxFromBoxAndDrawParams(
                  box,
                  false,
                  0,
                  otherHorizontalMargin,
                  otherVerticalMargin,
                ),
              );
        pathStartPoint = me.getConnectionCoordinatesFromBoxSideShift(
          startGridBox,
          startSide,
          startShift,
        );
        pathEndPoint = me.getConnectionCoordinatesFromBoxSideShift(
          endGridBox,
          endSide,
          endShift,
        );
        grid = me.buildPathGrid(
          startGridBox,
          endGridBox,
          pathStartPoint,
          pathEndPoint,
          startSide,
          endSide,
          otherBoxes,
        );
        gridStartPoint = me.convertDecartPointToGridPoint(grid, pathStartPoint);
        gridEndPoint = me.convertDecartPointToGridPoint(grid, pathEndPoint);
        path = me.findPathOnGrid(
          grid,
          gridStartPoint,
          gridEndPoint,
          startSide,
          endSide,
        );
      }
      for (
        lineDef = false;
        !path &&
        !lineDef &&
        noPathFallbackFn &&
        tryNum < noPathFallbackFn.length;
        tryNum++
      ) {
        lineDef = noPathFallbackFn[tryNum](lineDefFull, originalLineDef);
      }
    }
    if (path) {
      path = me.prependPathWithArrowStaffSegment(
        path,
        connStartPoint,
        startSide,
      );
      path = me.appendPathWithArrowStaffSegment(path, connEndPoint, endSide);
      path = me.optimizePath(path);
    }
    return path;
  }
  // Compares boxes relative position in the given direction.
  //  0 - 1 is to the left/top of 2
  //  1 - 1 overlaps with left/top edge of 2
  //  2 - 1 is inside 2
  // -2 - 2 is inside 1
  //  3 - 1 overlaps with right/bottom edge of 2
  //  4 - 1 is to the right/bottom of 2
  static calculateRelativePosition(box1, box2, vertical = false) {
    const startProp = vertical ? "top" : "start",
      endProp = vertical ? "bottom" : "end";
    let result;
    if (box1[endProp] < box2[startProp]) {
      result = 0;
    } else if (
      box1[endProp] <= box2[endProp] &&
      box1[endProp] >= box2[startProp] &&
      box1[startProp] < box2[startProp]
    ) {
      result = 1;
    } else if (
      box1[startProp] >= box2[startProp] &&
      box1[endProp] <= box2[endProp]
    ) {
      result = 2;
    } else if (
      box1[startProp] < box2[startProp] &&
      box1[endProp] > box2[endProp]
    ) {
      result = -2;
    } else if (
      box1[startProp] <= box2[endProp] &&
      box1[endProp] > box2[endProp]
    ) {
      result = 3;
    } else {
      result = 4;
    }
    return result;
  }
  // Checks if relative position of the original and marginized boxes is the same
  static boxOverlapChanged(
    startBox,
    endBox,
    gridStartBox,
    gridEndBox,
    vertical = false,
  ) {
    const calculateOverlap = _RectangularPathFinder.calculateRelativePosition,
      originalOverlap = calculateOverlap(startBox, endBox, vertical),
      finalOverlap = calculateOverlap(gridStartBox, gridEndBox, vertical);
    return originalOverlap !== finalOverlap;
  }
  shouldLookForPath(startBox, endBox, gridStartBox, gridEndBox) {
    let result = true;
    if (
      // We refer to the original arrow margins because during lookup those might be nullified and we need some
      // criteria to tell if events are too narrow
      (startBox.end - startBox.start <= this.startArrowMargin ||
        endBox.end - endBox.start <= this.endArrowMargin) &&
      Math.abs(
        _RectangularPathFinder.calculateRelativePosition(
          startBox,
          endBox,
          true,
        ),
      ) === 2
    ) {
      result = !_RectangularPathFinder.boxOverlapChanged(
        startBox,
        endBox,
        gridStartBox,
        gridEndBox,
      );
    }
    return result;
  }
  getConnectionCoordinatesFromBoxSideShift(box, side, shift) {
    let coords;
    switch (side) {
      case "left":
        coords = {
          x: box.start,
          y: (box.top + box.bottom) / 2 + shift,
        };
        break;
      case "right":
        coords = {
          x: box.end,
          y: (box.top + box.bottom) / 2 + shift,
        };
        break;
      case "top":
        coords = {
          x: (box.start + box.end) / 2 + shift,
          y: box.top,
        };
        break;
      case "bottom":
        coords = {
          x: (box.start + box.end) / 2 + shift,
          y: box.bottom,
        };
        break;
    }
    return coords;
  }
  calcGridBaseBoxFromBoxAndDrawParams(
    box,
    side,
    arrowMargin,
    horizontalMargin,
    verticalMargin,
  ) {
    let gridBox;
    switch (this.normalizeSide(side)) {
      case "left":
        gridBox = {
          start:
            box.start -
            Math.max(
              /*arrowSize + */
              arrowMargin,
              horizontalMargin,
            ),
          end: box.end + horizontalMargin,
          top: box.top - verticalMargin,
          bottom: box.bottom + verticalMargin,
        };
        break;
      case "right":
        gridBox = {
          start: box.start - horizontalMargin,
          end:
            box.end +
            Math.max(
              /*arrowSize + */
              arrowMargin,
              horizontalMargin,
            ),
          top: box.top - verticalMargin,
          bottom: box.bottom + verticalMargin,
        };
        break;
      case "top":
        gridBox = {
          start: box.start - horizontalMargin,
          end: box.end + horizontalMargin,
          top:
            box.top -
            Math.max(
              /*arrowSize + */
              arrowMargin,
              verticalMargin,
            ),
          bottom: box.bottom + verticalMargin,
        };
        break;
      case "bottom":
        gridBox = {
          start: box.start - horizontalMargin,
          end: box.end + horizontalMargin,
          top: box.top - verticalMargin,
          bottom:
            box.bottom +
            Math.max(
              /*arrowSize + */
              arrowMargin,
              verticalMargin,
            ),
        };
        break;
      default:
        gridBox = {
          start: box.start - horizontalMargin,
          end: box.end + horizontalMargin,
          top: box.top - verticalMargin,
          bottom: box.bottom + verticalMargin,
        };
    }
    return gridBox;
  }
  normalizeSide(side) {
    const { rtl } = this.client;
    (side2) => sideToSide[side2] || side2;
    if (side === "start") {
      return rtl ? "right" : "left";
    }
    if (side === "end") {
      return rtl ? "left" : "right";
    }
    return side;
  }
  buildPathGrid(
    startGridBox,
    endGridBox,
    pathStartPoint,
    pathEndPoint,
    startSide,
    endSide,
    otherGridBoxes,
  ) {
    let xs, ys, y, x, ix, iy, xslen, yslen, ib, blen, box, permitted, point;
    const points = {},
      linearPoints = [];
    xs = [
      startGridBox.start,
      startSide === "left" || startSide === "right"
        ? (startGridBox.start + startGridBox.end) / 2
        : pathStartPoint.x,
      startGridBox.end,
      endGridBox.start,
      endSide === "left" || endSide === "right"
        ? (endGridBox.start + endGridBox.end) / 2
        : pathEndPoint.x,
      endGridBox.end,
    ];
    ys = [
      startGridBox.top,
      startSide === "top" || startSide === "bottom"
        ? (startGridBox.top + startGridBox.bottom) / 2
        : pathStartPoint.y,
      startGridBox.bottom,
      endGridBox.top,
      endSide === "top" || endSide === "bottom"
        ? (endGridBox.top + endGridBox.bottom) / 2
        : pathEndPoint.y,
      endGridBox.bottom,
    ];
    if (otherGridBoxes) {
      otherGridBoxes.forEach((box2) => {
        xs.push(box2.start, (box2.start + box2.end) / 2, box2.end);
        ys.push(box2.top, (box2.top + box2.bottom) / 2, box2.bottom);
      });
    }
    xs = [...new Set(xs.sort((a, b) => a - b))];
    ys = [...new Set(ys.sort((a, b) => a - b))];
    for (iy = 0, yslen = ys.length; iy < yslen; ++iy) {
      points[iy] = points[iy] || {};
      y = ys[iy];
      for (ix = 0, xslen = xs.length; ix < xslen; ++ix) {
        x = xs[ix];
        permitted =
          (x <= startGridBox.start ||
            x >= startGridBox.end ||
            y <= startGridBox.top ||
            y >= startGridBox.bottom) &&
          (x <= endGridBox.start ||
            x >= endGridBox.end ||
            y <= endGridBox.top ||
            y >= endGridBox.bottom);
        if (otherGridBoxes) {
          for (
            ib = 0, blen = otherGridBoxes.length;
            permitted && ib < blen;
            ++ib
          ) {
            box = otherGridBoxes[ib];
            permitted =
              x <= box.start ||
              x >= box.end ||
              y <= box.top ||
              y >= box.bottom || // Allow point if it is a path start/end even if point is inside any box
              (x === pathStartPoint.x && y === pathStartPoint.y) ||
              (x === pathEndPoint.x && y === pathEndPoint.y);
          }
        }
        point = {
          distance: Number.MAX_SAFE_INTEGER,
          permitted,
          x,
          y,
          ix,
          iy,
        };
        points[iy][ix] = point;
        linearPoints.push(point);
      }
    }
    return {
      width: xs.length,
      height: ys.length,
      xs,
      ys,
      points,
      linearPoints,
    };
  }
  convertDecartPointToGridPoint(grid, point) {
    const x = grid.xs.indexOf(point.x),
      y = grid.ys.indexOf(point.y);
    return grid.points[y][x];
  }
  findPathOnGrid(grid, gridStartPoint, gridEndPoint, startSide, endSide) {
    const me = this;
    let path = false;
    if (gridStartPoint.permitted && gridEndPoint.permitted) {
      grid = me.waveForward(grid, gridStartPoint, 0);
      path = me.collectPath(grid, gridEndPoint, endSide);
    }
    return path;
  }
  // Returns neighbors from Von Neiman ambit (see Lee pathfinding algorithm description)
  getGridPointNeighbors(grid, gridPoint, predicateFn) {
    const ix = gridPoint.ix,
      iy = gridPoint.iy,
      result = [];
    let neighbor;
    if (iy < grid.height - 1) {
      neighbor = grid.points[iy + 1][ix];
      (!predicateFn || predicateFn(neighbor)) && result.push(neighbor);
    }
    if (iy > 0) {
      neighbor = grid.points[iy - 1][ix];
      (!predicateFn || predicateFn(neighbor)) && result.push(neighbor);
    }
    if (ix < grid.width - 1) {
      neighbor = grid.points[iy][ix + 1];
      (!predicateFn || predicateFn(neighbor)) && result.push(neighbor);
    }
    if (ix > 0) {
      neighbor = grid.points[iy][ix - 1];
      (!predicateFn || predicateFn(neighbor)) && result.push(neighbor);
    }
    return result;
  }
  waveForward(grid, gridStartPoint, distance) {
    const me = this;
    WalkHelper.preWalkUnordered(
      // Walk starting point - a node is a grid point and it's distance from the starting point
      [gridStartPoint, distance],
      // Children query function
      // NOTE: It's important to fix neighbor distance first, before waving to a neighbor, otherwise waving might
      //       get through a neighbor point setting it's distance to a value more than (distance + 1) whereas we,
      //       at the children querying moment in time, already know that the possibly optimal distance is (distance + 1)
      ([point, distance2]) =>
        me
          .getGridPointNeighbors(
            grid,
            point,
            (neighborPoint) =>
              neighborPoint.permitted && neighborPoint.distance > distance2 + 1,
          )
          .map(
            (neighborPoint) => [neighborPoint, distance2 + 1],
            // Neighbor distance fixation
          ),
      // Walk step iterator function
      ([point, distance2]) => (point.distance = distance2),
      // Neighbor distance applying
    );
    return grid;
  }
  collectPath(grid, gridEndPoint, endSide) {
    const me = this,
      path = [];
    let pathFound = true,
      neighbors,
      lowestDistanceNeighbor,
      xDiff,
      yDiff;
    while (pathFound && gridEndPoint.distance) {
      neighbors = me.getGridPointNeighbors(
        grid,
        gridEndPoint,
        (point) =>
          point.permitted && point.distance === gridEndPoint.distance - 1,
      );
      pathFound = neighbors.length > 0;
      if (pathFound) {
        neighbors = neighbors.sort((a, b) => {
          let xDiff2, yDiff2;
          xDiff2 = a.ix - gridEndPoint.ix;
          yDiff2 = a.iy - gridEndPoint.iy;
          const resultA =
            ((endSide === "left" || endSide === "right") && yDiff2 === 0) ||
            ((endSide === "top" || endSide === "bottom") && xDiff2 === 0)
              ? -1
              : 1;
          xDiff2 = b.ix - gridEndPoint.ix;
          yDiff2 = b.iy - gridEndPoint.iy;
          const resultB =
            ((endSide === "left" || endSide === "right") && yDiff2 === 0) ||
            ((endSide === "top" || endSide === "bottom") && xDiff2 === 0)
              ? -1
              : 1;
          if (resultA > resultB) return 1;
          if (resultA < resultB) return -1;
          if (resultA === resultB) return a.y > b.y ? -1 : a.y < b.y ? 1 : 0;
        });
        lowestDistanceNeighbor = neighbors[0];
        path.push({
          x1: lowestDistanceNeighbor.x,
          y1: lowestDistanceNeighbor.y,
          x2: gridEndPoint.x,
          y2: gridEndPoint.y,
        });
        xDiff = lowestDistanceNeighbor.ix - gridEndPoint.ix;
        yDiff = lowestDistanceNeighbor.iy - gridEndPoint.iy;
        switch (true) {
          case !yDiff && xDiff > 0:
            endSide = "left";
            break;
          case !yDiff && xDiff < 0:
            endSide = "right";
            break;
          case !xDiff && yDiff > 0:
            endSide = "top";
            break;
          case !xDiff && yDiff < 0:
            endSide = "bottom";
            break;
        }
        gridEndPoint = lowestDistanceNeighbor;
      }
    }
    return (pathFound && path.reverse()) || false;
  }
  prependPathWithArrowStaffSegment(path, connStartPoint, startSide) {
    if (path.length > 0) {
      const firstSegment = path[0],
        prependSegment = {
          x2: firstSegment.x1,
          y2: firstSegment.y1,
        };
      switch (startSide) {
        case "left":
          prependSegment.x1 = connStartPoint.x;
          prependSegment.y1 = firstSegment.y1;
          break;
        case "right":
          prependSegment.x1 = connStartPoint.x;
          prependSegment.y1 = firstSegment.y1;
          break;
        case "top":
          prependSegment.x1 = firstSegment.x1;
          prependSegment.y1 = connStartPoint.y;
          break;
        case "bottom":
          prependSegment.x1 = firstSegment.x1;
          prependSegment.y1 = connStartPoint.y;
          break;
      }
      path.unshift(prependSegment);
    }
    return path;
  }
  appendPathWithArrowStaffSegment(path, connEndPoint, endSide) {
    if (path.length > 0) {
      const lastSegment = path[path.length - 1],
        appendSegment = {
          x1: lastSegment.x2,
          y1: lastSegment.y2,
        };
      switch (endSide) {
        case "left":
          appendSegment.x2 = connEndPoint.x;
          appendSegment.y2 = lastSegment.y2;
          break;
        case "right":
          appendSegment.x2 = connEndPoint.x;
          appendSegment.y2 = lastSegment.y2;
          break;
        case "top":
          appendSegment.x2 = lastSegment.x2;
          appendSegment.y2 = connEndPoint.y;
          break;
        case "bottom":
          appendSegment.x2 = lastSegment.x2;
          appendSegment.y2 = connEndPoint.y;
          break;
      }
      path.push(appendSegment);
    }
    return path;
  }
  optimizePath(path) {
    const optPath = [];
    let prevSegment, curSegment;
    if (path.length > 0) {
      prevSegment = path.shift();
      optPath.push(prevSegment);
      while (path.length > 0) {
        curSegment = path.shift();
        if (
          equalEnough(prevSegment.x1, curSegment.x1) &&
          equalEnough(prevSegment.y1, curSegment.y1) &&
          equalEnough(prevSegment.x2, curSegment.x2) &&
          equalEnough(prevSegment.y2, curSegment.y2)
        ) {
          prevSegment = curSegment;
        } else if (
          equalEnough(prevSegment.y1, prevSegment.y2) &&
          equalEnough(curSegment.y1, curSegment.y2)
        ) {
          prevSegment.x2 = curSegment.x2;
        } else if (
          equalEnough(prevSegment.x1, prevSegment.x2) &&
          equalEnough(curSegment.x1, curSegment.x2)
        ) {
          prevSegment.y2 = curSegment.y2;
        } else {
          optPath.push(curSegment);
          prevSegment = curSegment;
        }
      }
    }
    return optPath;
  }
};
RectangularPathFinder._$name = "RectangularPathFinder";

// ../Scheduler/lib/Scheduler/feature/mixin/DependencyLineGenerator.js
function drawingDirection(pointSet) {
  if (pointSet.x1 === pointSet.x2) {
    return pointSet.y2 > pointSet.y1 ? "d" : "u";
  }
  return pointSet.x2 > pointSet.x1 ? "r" : "l";
}
function segmentLength(pointSet) {
  return pointSet.x1 === pointSet.x2
    ? pointSet.y2 - pointSet.y1
    : pointSet.x2 - pointSet.x1;
}
function arc(pointSet, nextPointSet, radius) {
  const corner = drawingDirection(pointSet) + drawingDirection(nextPointSet),
    rx = radius * (corner.includes("l") ? -1 : 1),
    ry = radius * (corner.includes("u") ? -1 : 1),
    sweep =
      corner === "ur" || corner === "lu" || corner === "dl" || corner === "rd"
        ? 1
        : 0;
  return `a${rx},${ry} 0 0 ${sweep} ${rx},${ry}`;
}
function line(pointSet, nextPointSet, location, radius, prevRadius) {
  let line2 = pointSet.x1 === pointSet.x2 ? "v" : "h",
    useRadius = radius;
  if (radius) {
    const length = segmentLength(pointSet),
      nextLength = nextPointSet
        ? Math.abs(segmentLength(nextPointSet))
        : Number.MAX_SAFE_INTEGER,
      sign = Math.sign(length);
    if (prevRadius == null) {
      prevRadius = radius;
    }
    if (Math.abs(length) < radius * 2 || nextLength < radius * 2) {
      useRadius = Math.min(Math.abs(length), nextLength) / 2;
    }
    const subtract =
        location === "single"
          ? 0
          : location === "first"
            ? useRadius
            : location === "between"
              ? prevRadius + useRadius
              : /*last*/
                prevRadius,
      useLength = length - subtract * sign;
    line2 += Math.sign(useLength) !== sign ? 0 : useLength;
    if (location !== "last" && location !== "single" && useRadius > 0) {
      line2 += ` ${arc(pointSet, nextPointSet, useRadius)}`;
    }
  } else {
    line2 += segmentLength(pointSet);
  }
  return {
    line: line2,
    currentRadius: radius !== useRadius ? useRadius : null,
  };
}
function pathMapper(radius, points) {
  const { length } = points;
  if (!length) {
    return "";
  }
  let currentRadius = null;
  return `M${points[0].x1},${points[0].y1} ${points
    .map((pointSet, i) => {
      const location =
          length === 1
            ? "single"
            : i === length - 1
              ? "last"
              : i === 0
                ? "first"
                : "between",
        lineSpec = line(
          pointSet,
          points[i + 1],
          location,
          radius,
          currentRadius,
        );
      ({ currentRadius } = lineSpec);
      return lineSpec.line;
    })
    .join(" ")}`;
}
var DependencyLineGenerator_default = (Target) => {
  var _a4;
  return (
    (_a4 = class extends Target {
      constructor() {
        super(...arguments);
        __publicField(this, "lineCache", {});
      }
      onSVGReady() {
        const me = this;
        me.pathFinder = new RectangularPathFinder({
          ...me.pathFinderConfig,
          client: me.client,
        });
        me.lineDefAdjusters = me.createLineDefAdjusters();
        me.createMarker();
      }
      changeRadius(radius) {
        if (radius !== null) {
          ObjectHelper.assertNumber(radius, "radius");
        }
        return radius;
      }
      resetAtRuntime() {
        if (!this.isConfiguring) {
          this.reset();
        }
      }
      updateRadius() {
        this.resetAtRuntime();
      }
      updateRenderer() {
        this.resetAtRuntime();
      }
      changeClickWidth(width) {
        if (width !== null) {
          ObjectHelper.assertNumber(width, "clickWidth");
        }
        return width;
      }
      updateClickWidth() {
        this.resetAtRuntime();
      }
      updateDrawAroundParents() {
        this.resetAtRuntime();
      }
      //region Marker
      createMarker() {
        var _a5, _b;
        const me = this,
          { markerDef } = me,
          svg = this.client.svgCanvas,
          markerId = markerDef ? `${me.client.id}-arrowEnd` : "arrowEnd";
        (_a5 = me.marker) == null ? void 0 : _a5.remove();
        svg.style.setProperty(
          "--scheduler-dependency-marker",
          `url(#${markerId})`,
        );
        me.marker = DomHelper.createElement({
          parent: svg,
          id: markerId,
          tag: "marker",
          className: "b-sch-dependency-arrow",
          ns: "http://www.w3.org/2000/svg",
          markerHeight: 11,
          markerWidth: 11,
          refX: 8.5,
          refY: 3,
          viewBox: "0 0 9 6",
          orient: "auto-start-reverse",
          markerUnits: "userSpaceOnUse",
          retainElement: true,
          children: [
            {
              tag: "path",
              ns: "http://www.w3.org/2000/svg",
              d: (_b = me.markerDef) != null ? _b : "M3,0 L3,6 L9,3 z",
            },
          ],
        });
      }
      updateMarkerDef() {
        if (!this.isConfiguring) {
          this.createMarker();
        }
      }
      //endregion
      //region DomConfig
      getAssignmentElement(assignment) {
        var _a5, _b;
        const proxyElement =
          (_b =
            (_a5 = this.client.features.eventDrag) == null
              ? void 0
              : _a5.getProxyElement) == null
            ? void 0
            : _b.call(_a5, assignment);
        return (
          proxyElement || this.client.getElementFromAssignmentRecord(assignment)
        );
      }
      // Generate a DomConfig for a dependency line between two assignments (tasks in Gantt)
      getDomConfigs(dependency, fromAssignment, toAssignment, forceBoxes) {
        var _a5, _b;
        const me = this,
          key = me.getDependencyKey(dependency, fromAssignment, toAssignment),
          cached = me.lineCache[key];
        if (
          me.constructLineCache ||
          !cached ||
          forceBoxes ||
          (me.drawingLive &&
            (me.getAssignmentElement(fromAssignment) ||
              me.getAssignmentElement(toAssignment)))
        ) {
          const lineDef = me.prepareLineDef(
              dependency,
              fromAssignment,
              toAssignment,
              forceBoxes,
            ),
            points =
              lineDef && me.pathFinder.findPath(lineDef, me.lineDefAdjusters),
            { client, clickWidth } = me,
            { toEvent } = dependency;
          if (points) {
            const highlighted = me.highlighted.get(dependency),
              domConfig = {
                tag: "path",
                ns: "http://www.w3.org/2000/svg",
                d: pathMapper((_a5 = me.radius) != null ? _a5 : 0, points),
                role: "presentation",
                dataset: {
                  syncId: key,
                  depId: dependency.id,
                  fromId: fromAssignment.id,
                  toId: toAssignment.id,
                },
                elementData: {
                  dependency,
                  points,
                },
                class: {
                  [me.baseCls]: 1,
                  [dependency.cls]: dependency.cls,
                  // Data highlight
                  [dependency.highlighted]: dependency.highlighted,
                  // Feature highlight
                  [highlighted && [...highlighted].join(" ")]: highlighted,
                  [me.noMarkerCls]: lineDef.hideMarker,
                  "b-inactive": dependency.active === false,
                  "b-sch-bidirectional-line": dependency.bidirectional,
                  "b-readonly": dependency.readOnly,
                  // If target event is outside the view add special CSS class to hide marker (arrow)
                  "b-sch-dependency-ends-outside":
                    (!toEvent.milestone &&
                      (toEvent.endDate <= client.startDate ||
                        client.endDate <= toEvent.startDate)) ||
                    (toEvent.milestone &&
                      (toEvent.endDate < client.startDate ||
                        client.endDate < toEvent.startDate)),
                },
              };
            (_b = me.renderer) == null
              ? void 0
              : _b.call(me, {
                  domConfig,
                  points,
                  dependencyRecord: dependency,
                  fromAssignmentRecord: fromAssignment,
                  toAssignmentRecord: toAssignment,
                  fromBox: lineDef.startBox,
                  toBox: lineDef.endBox,
                  fromSide: lineDef.startSide,
                  toSide: lineDef.endSide,
                });
            const configs = [domConfig];
            if (clickWidth > 1) {
              configs.push({
                ...domConfig,
                // Shallow on purpose, to not waste perf cloning deeply
                class: {
                  ...domConfig.class,
                  "b-click-area": 1,
                },
                dataset: {
                  ...domConfig.dataset,
                  syncId: `${domConfig.dataset.syncId}-click-area`,
                },
                style: {
                  strokeWidth: clickWidth,
                },
              });
            }
            return (me.lineCache[key] = configs);
          }
          return (me.lineCache[key] = null);
        }
        return cached;
      }
      //endregion
      //region Bounds
      // Generates `otherBoxes` config for rectangular path finder, which push dependency line to the row boundary.
      // It should be enough to return single box with top/bottom taken from row top/bottom and left/right taken from source
      // box, extended by start arrow margin to both sides.
      generateBoundaryBoxes(box, side) {
        if (side === "top") {
          return [];
        }
        if (side === "bottom") {
          return [
            {
              start: box.left,
              end: box.left + box.width / 2,
              top: box.rowTop,
              bottom: box.rowBottom,
            },
            {
              start: box.left + box.width / 2,
              end: box.right,
              top: box.rowTop,
              bottom: box.rowBottom,
            },
          ];
        } else {
          return [
            {
              start: box.left - this.pathFinder.startArrowMargin,
              end: box.right + this.pathFinder.startArrowMargin,
              top: box.rowTop,
              bottom: box.rowBottom,
            },
          ];
        }
      }
      // Bounding box for an assignment, uses elements bounds if rendered
      getAssignmentBounds(assignment) {
        const { client } = this,
          element = this.getAssignmentElement(assignment);
        if (element && !client.isExporting) {
          const rectangle = Rectangle.from(element, this.relativeTo);
          if (client.isHorizontal) {
            let row = client.getRowById(assignment.resource.id);
            if (row) {
              if (rectangle.y < row.top || rectangle.bottom > row.bottom) {
                const overRow = client.rowManager.getRowAt(
                  rectangle.center.y,
                  true,
                );
                if (overRow) {
                  row = overRow;
                }
              }
              rectangle.rowTop = row.top;
              rectangle.rowBottom = row.bottom;
            } else {
              return client.getAssignmentEventBox(assignment, true);
            }
          }
          return rectangle;
        }
        return (
          client.isEngineReady && client.getAssignmentEventBox(assignment, true)
        );
      }
      //endregion
      //region Sides
      getConnectorStartSide(timeSpanRecord) {
        return this.client.currentOrientation.getConnectorStartSide(
          timeSpanRecord,
        );
      }
      getConnectorEndSide(timeSpanRecord) {
        return this.client.currentOrientation.getConnectorEndSide(
          timeSpanRecord,
        );
      }
      getDependencyStartSide(dependency) {
        const { fromEvent, type, fromSide } = dependency;
        if (fromSide) {
          return fromSide;
        }
        switch (true) {
          case type === DependencyModel.Type.StartToEnd:
          case type === DependencyModel.Type.StartToStart:
            return this.getConnectorStartSide(fromEvent);
          case type === DependencyModel.Type.EndToStart:
          case type === DependencyModel.Type.EndToEnd:
            return this.getConnectorEndSide(fromEvent);
          default:
            return this.getConnectorEndSide(fromEvent);
        }
      }
      getDependencyEndSide(dependency) {
        const { toEvent, type, toSide } = dependency;
        if (toSide) {
          return toSide;
        }
        switch (true) {
          case type === DependencyModel.Type.EndToEnd:
          case type === DependencyModel.Type.StartToEnd:
            return this.getConnectorEndSide(toEvent);
          case type === DependencyModel.Type.EndToStart:
          case type === DependencyModel.Type.StartToStart:
            return this.getConnectorStartSide(toEvent);
          default:
            return this.getConnectorStartSide(toEvent);
        }
      }
      //endregion
      //region Line def
      // An array of functions used to alter path config when no path found.
      // It first tries to shrink arrow margins and secondly hides arrows entirely
      createLineDefAdjusters() {
        var _a5;
        const { client } = this;
        function shrinkArrowMargins(lineDef) {
          const { barMargin } = client;
          if (
            lineDef.startArrowMargin > barMargin ||
            lineDef.endArrowMargin > barMargin
          ) {
            lineDef.startArrowMargin = lineDef.endArrowMargin = barMargin;
            return lineDef;
          }
          return false;
        }
        function resetArrowMargins(lineDef) {
          if (lineDef.startArrowMargin > 0 || lineDef.endArrowMargin > 0) {
            lineDef.startArrowMargin = lineDef.endArrowMargin = 0;
            return lineDef;
          }
          return false;
        }
        function shrinkHorizontalMargin(lineDef, originalLineDef) {
          if (lineDef.horizontalMargin > 2) {
            lineDef.horizontalMargin = 1;
            originalLineDef.hideMarker = true;
            return lineDef;
          }
          return false;
        }
        const adjusters = [
          shrinkArrowMargins,
          resetArrowMargins,
          shrinkHorizontalMargin,
        ];
        if (
          (_a5 = client.features.nestedEvents) == null ? void 0 : _a5.enabled
        ) {
          adjusters.unshift((lineDef) => {
            if (lineDef.otherBoxes.length) {
              lineDef.otherBoxes.length = lineDef.otherBoxes.nestedStart;
            }
            return lineDef;
          });
        }
        return adjusters;
      }
      // Overridden in Gantt
      adjustLineDef(dependency, lineDef) {
        return lineDef;
      }
      // Prepare data to feed to the path finder
      prepareLineDef(dependency, fromAssignment, toAssignment, forceBoxes) {
        var _a5, _b, _c, _d;
        const me = this,
          startSide = me.getDependencyStartSide(dependency),
          endSide = me.getDependencyEndSide(dependency),
          startRectangle =
            (_a5 = forceBoxes == null ? void 0 : forceBoxes.from) != null
              ? _a5
              : me.getAssignmentBounds(fromAssignment),
          endRectangle =
            (_b = forceBoxes == null ? void 0 : forceBoxes.to) != null
              ? _b
              : me.getAssignmentBounds(toAssignment),
          otherBoxes = [];
        if (!startRectangle || !endRectangle) {
          return null;
        }
        let { startArrowMargin, verticalMargin } = me.pathFinder;
        if (me.client.isHorizontal) {
          if (
            startRectangle.rowTop != null &&
            startRectangle.rowTop !== endRectangle.rowTop
          ) {
            otherBoxes.push(
              ...me.generateBoundaryBoxes(startRectangle, startSide),
            );
          }
          if (
            ((_c = me.client.features.nestedEvents) == null
              ? void 0
              : _c.enabled) &&
            me.drawAroundParents
          ) {
            const { resourceStore } = me.client,
              fromResource = fromAssignment.resource,
              toResource = toAssignment.resource,
              fromIndex = resourceStore.indexOf(fromResource),
              toIndex = resourceStore.indexOf(toResource),
              minIndex = Math.min(fromIndex, toIndex),
              maxIndex = Math.max(fromIndex, toIndex);
            otherBoxes.nestedStart = otherBoxes.length;
            for (const assignment of me.client.assignmentStore) {
              if (
                assignment !== fromAssignment &&
                assignment !== toAssignment &&
                ((_d = assignment.event) == null ? void 0 : _d.isParent) &&
                fromAssignment.event.parent !== assignment.event &&
                toAssignment.event.parent !== assignment.event
              ) {
                const currentIndex = resourceStore.indexOf(assignment.resource);
                if (currentIndex >= minIndex && currentIndex <= maxIndex) {
                  const assignmentBox = me
                    .getAssignmentBounds(assignment)
                    .inflate(startArrowMargin);
                  assignmentBox.isNestedParent = true;
                  otherBoxes.push(assignmentBox);
                }
              }
            }
          }
          if (!dependency.bidirectional) {
            if (/(top|bottom)/.test(startSide)) {
              startArrowMargin = me.client.barMargin / 2;
            }
            verticalMargin = me.client.barMargin / 2;
          }
        }
        return me.adjustLineDef(dependency, {
          startBox: startRectangle,
          endBox: endRectangle,
          otherBoxes,
          startArrowMargin,
          verticalMargin,
          otherVerticalMargin: 0,
          otherHorizontalMargin: 0,
          startSide,
          endSide,
        });
      }
      //endregion
      //region Cache
      // All dependencies are about to be drawn, check if we need to build the line cache
      beforeDraw() {
        super.beforeDraw();
        if (!Object.keys(this.lineCache).length) {
          this.constructLineCache = true;
        }
      }
      // All dependencies are drawn, we no longer need to rebuild the cache
      afterDraw() {
        super.afterDraw();
        this.constructLineCache = false;
      }
      reset() {
        super.reset();
        this.lineCache = {};
      }
      //endregion
    }),
    __publicField(_a4, "$name", "DependencyLineGenerator"),
    _a4
  );
};

// ../Scheduler/lib/Scheduler/feature/mixin/DependencyTooltip.js
var fromBoxSide = ["start", "start", "end", "end"];
var toBoxSide = ["start", "end", "start", "end"];
var DependencyTooltip_default = (Target) => {
  var _a4;
  return (
    (_a4 = class extends Target {
      changeTooltip(tooltip, old) {
        const me = this;
        old == null ? void 0 : old.destroy();
        if (!me.showTooltip || !tooltip) {
          return null;
        }
        return Tooltip.new(
          {
            align: "b-t",
            id: `${me.client.id}-dependency-tip`,
            forSelector: `.b-timelinebase:not(.b-eventeditor-editing,.b-taskeditor-editing,.b-resizing-event,.b-dragcreating,.b-dragging-event,.b-creating-dependency) .${me.baseCls}`,
            forElement: me.client.timeAxisSubGridElement,
            showOnHover: true,
            hoverDelay: 0,
            hideDelay: 0,
            anchorToTarget: false,
            textContent: false,
            // Skip max-width setting
            trackMouse: false,
            getHtml: me.getHoverTipHtml.bind(me),
          },
          tooltip,
        );
      }
      /**
       * Generates DomConfig content for the tooltip shown when hovering a dependency
       * @param {Object} tooltipConfig
       * @returns {DomConfig} DomConfig used as tooltips content
       * @private
       */
      getHoverTipHtml({ activeTarget }) {
        return this.tooltipTemplate(this.resolveDependencyRecord(activeTarget));
      }
    }),
    __publicField(_a4, "$name", "DependencyTooltip"),
    __publicField(_a4, "configurable", {
      /**
       * Set to `true` to show a tooltip when hovering a dependency line
       * @config {Boolean}
       * @default
       * @category Dependency tooltip
       */
      showTooltip: true,
      /**
       * Set to `true` to show the lag in the tooltip
       * @config {Boolean}
       * @default
       */
      showLagInTooltip: false,
      /**
       * A template function allowing you to configure the contents of the tooltip shown when hovering a
       * dependency line. You can return either an HTML string or a {@link DomConfig} object.
       * @prp {Function} tooltipTemplate
       * @param {Scheduler.model.DependencyBaseModel} dependency The dependency record
       * @returns {String|DomConfig}
       * @category Dependency tooltip
       */
      tooltipTemplate(dependency) {
        const me = this;
        return {
          children: [
            {
              className: "b-sch-dependency-tooltip",
              children: [
                { tag: "label", text: me.L("L{Dependencies.from}") },
                { text: dependency.fromEvent.name },
                {
                  className: `b-sch-box b-${dependency.fromSide || fromBoxSide[dependency.type]}`,
                },
                { tag: "label", text: me.L("L{Dependencies.to}") },
                { text: dependency.toEvent.name },
                {
                  className: `b-sch-box b-${dependency.toSide || toBoxSide[dependency.type]}`,
                },
                me.showLagInTooltip && {
                  tag: "label",
                  text: me.L("L{DependencyEdit.Lag}"),
                },
                me.showLagInTooltip && {
                  text: `${dependency.lag || 0} ${DateHelper.getLocalizedNameOfUnit(dependency.lagUnit, dependency.lag !== 1)}`,
                },
              ],
            },
          ],
        };
      },
      /**
       * A tooltip config object that will be applied to the dependency hover tooltip. Can be used to for example
       * customize delay
       * @config {TooltipConfig}
       * @category Dependency tooltip
       */
      tooltip: {
        $config: "nullify",
        value: {},
      },
    }),
    _a4
  );
};

// ../Scheduler/lib/Scheduler/feature/Dependencies.js
var eventNameMap2 = {
  click: "Click",
  dblclick: "DblClick",
  contextmenu: "ContextMenu",
};
var emptyObject15 = Object.freeze({});
var collectLinkedAssignments = (assignment) => {
  var _a4;
  const result = [assignment];
  if ((_a4 = assignment.resource) == null ? void 0 : _a4.hasLinks) {
    result.push(
      ...assignment.resource.$links.map((l) => ({
        id: `${l.id}_${assignment.id}`,
        resource: l,
        event: assignment.event,
        drawDependencies: assignment.drawDependencies,
      })),
    );
  }
  return result;
};
var Dependencies = class extends InstancePlugin.mixin(
  AttachToProjectMixin_default,
  Delayable_default,
  DependencyCreation_default,
  DependencyGridCache_default,
  DependencyLineGenerator_default,
  DependencyTooltip_default,
) {
  constructor() {
    super(...arguments);
    __publicField(this, "domConfigs", /* @__PURE__ */ new Map());
    __publicField(this, "drawingLive", false);
    __publicField(this, "lastScrollX", null);
    __publicField(this, "highlighted", /* @__PURE__ */ new Map());
    // Cached lookups
    __publicField(this, "visibleResources", null);
    __publicField(this, "usingLinks", null);
    __publicField(this, "visibleDateRange", null);
    __publicField(this, "relativeTo", null);
  }
  static get pluginConfig() {
    return {
      chain: [
        "render",
        "onInternalPaint",
        "onElementClick",
        "onElementDblClick",
        "onElementContextMenu",
        "onElementMouseOver",
        "onElementMouseOut",
        "bindStore",
      ],
      assign: [
        "getElementForDependency",
        "getElementsForDependency",
        "resolveDependencyRecord",
      ],
    };
  }
  //endregion
  //region Init & destroy
  construct(client, config) {
    super.construct(client, config);
    const { scheduledEventName } = client;
    client.ion({
      svgCanvasCreated: "onSVGReady",
      // These events trigger live refresh behaviour
      animationStart: "refresh",
      // eventDrag in Scheduler, taskDrag in Gantt
      [scheduledEventName + "DragStart"]: "refresh",
      [scheduledEventName + "DragAbort"]: "refresh",
      [scheduledEventName + "ResizeStart"]: "refresh",
      [scheduledEventName + "SegmentDragStart"]: "refresh",
      [scheduledEventName + "SegmentResizeStart"]: "refresh",
      // These events shift the surroundings to such extent that grid cache needs rebuilding to be sure that
      // all dependencies are considered
      timelineViewportResize: "reset",
      timeAxisViewModelUpdate: "reset",
      toggleNode: "reset",
      thisObj: this,
    });
    client.rowManager.ion({
      refresh: "reset",
      // For example when changing barMargin or rowHeight
      changeTotalHeight: "reset",
      // For example when collapsing groups
      thisObj: this,
    });
    this.bindStore(client.store);
  }
  doDisable(disable) {
    if (!this.isConfiguring) {
      this._isDisabling = disable;
      this.draw();
      this._isDisabling = false;
    }
    super.doDisable(disable);
  }
  //endregion
  //region RefreshTriggers
  get rowStore() {
    return this.client.isVertical
      ? this.client.resourceStore
      : this.client.store;
  }
  // React to replacing or refreshing a display store
  bindStore(store) {
    const me = this;
    if (!me.client.isVertical) {
      me.detachListeners("store");
      if (me.client.usesDisplayStore) {
        store == null
          ? void 0
          : store.ion({
              name: "store",
              refresh: "onStoreRefresh",
              thisObj: me,
            });
        me.reset();
      }
    }
  }
  onStoreRefresh() {
    this.reset();
  }
  attachToProject(project) {
    super.attachToProject(project);
    project == null
      ? void 0
      : project.ion({
          name: "project",
          commitFinalized: "reset",
          thisObj: this,
        });
  }
  attachToResourceStore(resourceStore) {
    super.attachToResourceStore(resourceStore);
    resourceStore == null
      ? void 0
      : resourceStore.ion({
          name: "resourceStore",
          change: "onResourceStoreChange",
          refresh: "onResourceStoreChange",
          thisObj: this,
        });
  }
  onResourceStoreChange() {
    this.usingLinks = null;
    this.reset();
  }
  attachToEventStore(eventStore) {
    super.attachToEventStore(eventStore);
    eventStore == null
      ? void 0
      : eventStore.ion({
          name: "eventStore",
          refresh: "reset",
          thisObj: this,
        });
  }
  attachToAssignmentStore(assignmentStore) {
    super.attachToAssignmentStore(assignmentStore);
    assignmentStore == null
      ? void 0
      : assignmentStore.ion({
          name: "assignmentStore",
          refresh: "reset",
          thisObj: this,
        });
  }
  attachToDependencyStore(dependencyStore) {
    super.attachToDependencyStore(dependencyStore);
    dependencyStore == null
      ? void 0
      : dependencyStore.ion({
          name: "dependencyStore",
          change: "reset",
          refresh: "reset",
          thisObj: this,
        });
  }
  updateDrawOnScroll(drawOnScroll) {
    const me = this;
    me.detachListeners("scroll");
    if (drawOnScroll) {
      me.client.ion({
        name: "scroll",
        scroll: "doRefresh",
        horizontalScroll: "onHorizontalScroll",
        prio: -100,
        // After Scheduler draws on scroll, since we target elements
        thisObj: me,
      });
    } else {
      me.client.scrollable.ion({
        name: "scroll",
        scrollEnd: "draw",
        thisObj: me,
      });
      me.client.timeAxisSubGrid.scrollable.ion({
        name: "scroll",
        scrollEnd: "draw",
        thisObj: me,
      });
    }
  }
  onHorizontalScroll({ subGrid, scrollX }) {
    if (
      scrollX !== this.lastScrollX &&
      subGrid === this.client.timeAxisSubGrid
    ) {
      this.lastScrollX = scrollX;
      this.draw();
    }
  }
  onInternalPaint() {
    this.refresh();
  }
  //endregion
  //region Dependency types
  // Used by DependencyField
  static getLocalizedDependencyType(type) {
    return type ? this.L(`L{DependencyType.${type}}`) : "";
  }
  //endregion
  //region Elements
  getElementForDependency(dependency, fromAssignment, toAssignment) {
    return this.getElementsForDependency(
      dependency,
      fromAssignment,
      toAssignment,
    )[0];
  }
  // NOTE: If we ever make this public we should change it to use the syncIdMap. Currently not needed since only
  // used in tests
  getElementsForDependency(dependency, fromAssignment, toAssignment) {
    let selector = `[data-dep-id="${dependency.id}"]`;
    if (fromAssignment) {
      selector += `[data-from-id="${fromAssignment.id}"]`;
    }
    if (toAssignment) {
      selector += `[data-to-id="${toAssignment.id}"]`;
    }
    return Array.from(this.client.svgCanvas.querySelectorAll(selector));
  }
  /**
   * Returns the dependency record for a DOM element
   * @param {HTMLElement} element The dependency line element
   * @returns {Scheduler.model.DependencyModel} The dependency record
   */
  resolveDependencyRecord(element) {
    var _a4;
    return (_a4 = element.elementData) == null ? void 0 : _a4.dependency;
  }
  isDependencyElement(element) {
    return element.matches(`.${this.baseCls}`);
  }
  //endregion
  //region DOM Events
  onElementClick(event) {
    const dependency = this.resolveDependencyRecord(event.target);
    if (dependency) {
      const eventName = eventNameMap2[event.type];
      this.client.trigger(`dependency${eventName}`, {
        dependency,
        event,
      });
    }
  }
  onElementDblClick(event) {
    return this.onElementClick(event);
  }
  onElementContextMenu(event) {
    return this.onElementClick(event);
  }
  onElementMouseOver(event) {
    const me = this,
      dependency = me.resolveDependencyRecord(event.target);
    if (dependency) {
      me.client.trigger("dependencyMouseOver", {
        dependency,
        event,
      });
      if (me.overCls) {
        me.highlight(dependency);
      }
    }
  }
  onElementMouseOut(event) {
    const me = this,
      dependency = me.resolveDependencyRecord(event.target);
    if (dependency) {
      me.client.trigger("dependencyMouseOut", {
        dependency,
        event,
      });
      if (me.overCls) {
        me.unhighlight(dependency);
      }
    }
  }
  //endregion
  //region Export
  // Export calls this fn to determine if a dependency should be included or not
  isDependencyVisible(dependency) {
    const me = this,
      { rowStore } = me,
      { fromEvent, toEvent } = dependency;
    if (!fromEvent || !toEvent) {
      return false;
    }
    const fromResource = fromEvent.resource,
      toResource = toEvent.resource;
    if (
      !rowStore.isAvailable(fromResource) ||
      !rowStore.isAvailable(toResource)
    ) {
      return false;
    }
    return (
      fromEvent.isModel &&
      !fromResource.instanceMeta(rowStore).hidden &&
      !toResource.instanceMeta(rowStore).hidden
    );
  }
  //endregion
  //region Highlight
  updateHighlightDependenciesOnEventHover(enable) {
    const me = this;
    if (enable) {
      const { client } = me;
      client.ion({
        name: "highlightOnHover",
        [`${client.scheduledEventName}MouseEnter`]: (params) =>
          me.highlightEventDependencies(
            params.eventRecord || params.taskRecord,
          ),
        [`${client.scheduledEventName}MouseLeave`]: (params) =>
          me.unhighlightEventDependencies(
            params.eventRecord || params.taskRecord,
          ),
        thisObj: me,
      });
    } else {
      me.detachListeners("highlightOnHover");
    }
  }
  highlight(dependency, cls2 = this.overCls) {
    let classes = this.highlighted.get(dependency);
    if (!classes) {
      this.highlighted.set(dependency, (classes = /* @__PURE__ */ new Set()));
    }
    classes.add(cls2);
    for (const element of this.getElementsForDependency(dependency)) {
      element.classList.add(cls2);
    }
  }
  unhighlight(dependency, cls2 = this.overCls) {
    var _a4;
    const classes =
      (_a4 = this.highlighted) == null ? void 0 : _a4.get(dependency);
    if (classes) {
      classes.delete(cls2);
      if (!classes.size) {
        this.highlighted.delete(dependency);
      }
    }
    for (const element of this.getElementsForDependency(dependency)) {
      element.classList.remove(cls2);
    }
  }
  highlightEventDependencies(timespan, cls2) {
    timespan.dependencies.forEach((dep) => this.highlight(dep, cls2));
  }
  unhighlightEventDependencies(timespan, cls2) {
    timespan.dependencies.forEach((dep) => this.unhighlight(dep, cls2));
  }
  //endregion
  //region Drawing
  // Implemented in DependencyGridCache to return dependencies that might intersect the current viewport and thus
  // should be considered for drawing. Fallback value here is used when there is no grid cache (which happens when it
  // is reset. Also useful in case we want to have it configurable or opt out automatically for small datasets)
  getDependenciesToConsider(startMS, endMS, startIndex, endIndex) {
    var _a4, _b;
    const { eventStore } = this.project;
    return (_b =
      (_a4 = super.getDependenciesToConsider) == null
        ? void 0
        : _a4.call(this, startMS, endMS, startIndex, endIndex)) != null
      ? _b
      : // Falling back to using all valid deps (fix for not trying to draw conflicted deps)
        this.project.dependencyStore.records.filter(
          (d) =>
            (d.isValid && !eventStore.isFiltered) ||
            (eventStore.isAvailable(d.fromEvent) &&
              eventStore.isAvailable(d.toEvent)),
        );
  }
  // String key used as syncId
  getDependencyKey(dependency, fromAssignment, toAssignment) {
    return `dep:${dependency.id};from:${fromAssignment.id};to:${toAssignment.id}`;
  }
  drawDependency(dependency, batch = false, forceBoxes = null) {
    var _a4, _b, _c, _d;
    const me = this,
      { domConfigs, client, rowStore, topIndex, bottomIndex } = me,
      { useInitialAnimation } = client,
      { idMap } = rowStore,
      { startMS, endMS } = me.visibleDateRange,
      { fromEvent, toEvent } = dependency;
    let fromAssigned = fromEvent.assigned,
      toAssigned = toEvent.assigned;
    if (
      // No point in trying to draw dep between unscheduled/non-existing events
      fromEvent.isScheduled &&
      toEvent.isScheduled && // Or unassigned ones
      (fromAssigned == null ? void 0 : fromAssigned.size) &&
      (toAssigned == null ? void 0 : toAssigned.size)
    ) {
      if (me.usingLinks) {
        fromAssigned = [...fromAssigned].flatMap(collectLinkedAssignments);
        toAssigned = [...toAssigned].flatMap(collectLinkedAssignments);
      }
      for (const from of fromAssigned) {
        for (const to of toAssigned) {
          const fromIndex =
              (_b = idMap[(_a4 = from.resource) == null ? void 0 : _a4.id]) ==
              null
                ? void 0
                : _b.index,
            toIndex =
              (_d = idMap[(_c = to.resource) == null ? void 0 : _c.id]) == null
                ? void 0
                : _d.index,
            fromDateMS = Math.min(fromEvent.startDateMS, toEvent.startDateMS),
            toDateMS = Math.max(fromEvent.endDateMS, toEvent.endDateMS);
          if (
            client.isExporting ||
            (fromIndex != null &&
              toIndex != null &&
              from.drawDependencies !== false &&
              to.drawDependencies !== false &&
              rowStore.isAvailable(from.resource) &&
              rowStore.isAvailable(to.resource) &&
              !(
                // Both ends above view
                (
                  (fromIndex < topIndex && toIndex < topIndex) || // Both ends below view
                  (fromIndex > bottomIndex && toIndex > bottomIndex) || // Both ends before view
                  (fromDateMS < startMS && toDateMS < startMS) || // Both ends after view
                  (fromDateMS > endMS && toDateMS > endMS)
                )
              ))
          ) {
            const key = me.getDependencyKey(dependency, from, to),
              lineDomConfigs = me.getDomConfigs(
                dependency,
                from,
                to,
                forceBoxes,
              );
            if (lineDomConfigs) {
              if (useInitialAnimation) {
                lineDomConfigs[0].style = {
                  animationDelay: `${(Math.max(fromIndex, toIndex) / 20) * 1e3}ms`,
                };
              }
              domConfigs.set(key, lineDomConfigs);
            } else {
              domConfigs.delete(key);
            }
          }
          me.afterDrawDependency(
            dependency,
            fromIndex,
            toIndex,
            fromDateMS,
            toDateMS,
          );
        }
      }
    }
    if (!batch) {
      me.domSync();
    }
  }
  // Hooks used by grid cache, to keep code in this file readable
  afterDrawDependency(dependency, fromIndex, toIndex, fromDateMS, toDateMS) {
    var _a4;
    (_a4 = super.afterDrawDependency) == null
      ? void 0
      : _a4.call(this, dependency, fromIndex, toIndex, fromDateMS, toDateMS);
  }
  beforeDraw() {
    var _a4;
    (_a4 = super.beforeDraw) == null ? void 0 : _a4.call(this);
  }
  afterDraw() {
    var _a4;
    (_a4 = super.afterDraw) == null ? void 0 : _a4.call(this);
  }
  // Update DOM
  domSync(targetElement = this.client.svgCanvas, batch = false) {
    DomSync.sync({
      targetElement,
      domConfig: {
        onlyChildren: true,
        children: Array.from(this.domConfigs.values()).flat(),
      },
      syncIdField: "syncId",
      releaseThreshold: 0,
      strict: true,
      callback() {},
    });
    if (batch) {
      this.clearDomConfigs();
    }
  }
  fillDrawingCache() {
    const me = this,
      { client } = me;
    me.relativeTo = Rectangle.from(client.svgCanvas);
    me.visibleResources = client.visibleResources;
    me.visibleDateRange = client.visibleDateRange;
    me.topIndex = me.rowStore.indexOf(me.visibleResources.first);
    me.bottomIndex = me.rowStore.indexOf(me.visibleResources.last);
    if (me.usingLinks == null) {
      me.usingLinks = client.resourceStore.some((r) => r.hasLinks);
    }
  }
  clearDomConfigs() {
    this.domConfigs.clear();
  }
  // Draw all dependencies intersecting the current viewport immediately
  draw() {
    const me = this,
      { client } = me,
      { visibleDateRange } = client;
    if (
      client.refreshSuspended ||
      !client.foregroundCanvas ||
      !visibleDateRange ||
      !client.isEngineReady ||
      (me.disabled && !me._isDisabling) ||
      client.isExporting
    ) {
      return;
    }
    me.fillDrawingCache();
    me.clearDomConfigs();
    if (
      client.firstVisibleRow &&
      client.lastVisibleRow &&
      client.timeAxis.count &&
      !me.disabled &&
      visibleDateRange.endMS - visibleDateRange.startMS > 0
    ) {
      const { topIndex, bottomIndex } = me,
        dependencies = me.getDependenciesToConsider(
          visibleDateRange.startMS,
          visibleDateRange.endMS,
          topIndex,
          bottomIndex,
        );
      me.beforeDraw();
      for (const dependency of dependencies) {
        me.drawDependency(dependency, true);
      }
      me.afterDraw();
    }
    me.domSync();
    client.trigger("dependenciesDrawn");
  }
  //endregion
  //region Refreshing
  // Performs a draw on next frame, not intended to be called directly, call refresh() instead
  doRefresh() {
    var _a4, _b, _c, _d, _e;
    const me = this,
      { client } = me,
      { scheduledEventName, features } = client;
    me.draw();
    me.drawingLive =
      client.dependencyStore.count &&
      (client.isAnimating ||
        (client.useInitialAnimation && client.eventStore.count) ||
        ((_a4 = features[`${scheduledEventName}Drag`]) == null
          ? void 0
          : _a4.isActivelyDragging) ||
        ((_b = features[`${scheduledEventName}Drag`]) == null
          ? void 0
          : _b.isAborting) ||
        ((_c = features[`${scheduledEventName}Resize`]) == null
          ? void 0
          : _c.isResizing) ||
        ((_d = features[`${scheduledEventName}SegmentDrag`]) == null
          ? void 0
          : _d.isActivelyDragging) ||
        ((_e = features[`${scheduledEventName}SegmentResize`]) == null
          ? void 0
          : _e.isResizing));
    me.drawingLive && me.refresh(false, true);
  }
  rafRefresh() {
    this.doRefresh.now();
  }
  /**
   * Redraws dependencies on the next animation frame
   */
  refresh(immediateRefresh = this.immediateRefresh, rafRefresh = false) {
    const me = this,
      { client } = me;
    if (
      !client.refreshSuspended &&
      !me.disabled &&
      client.isPainted &&
      !client.timeAxisSubGrid.collapsed
    ) {
      if (immediateRefresh) {
        me.doRefresh.now();
      } else if (rafRefresh) {
        me.rafRefresh();
      } else {
        me.doRefresh();
      }
    }
  }
  // Resets grid cache and performs a draw on next frame. Conditions when it should be called:
  // * Zooming
  // * Shifting time axis
  // * Resizing window
  // * CRUD
  // ...
  reset({ source, type } = emptyObject15) {
    var _a4;
    (_a4 = super.reset) == null ? void 0 : _a4.call(this);
    this.refresh(source === this.client && type === "timelineviewportresize");
  }
  /**
   * Draws all dependencies for the specified task.
   * @deprecated 5.1 The Dependencies feature was refactored and this fn is no longer needed
   */
  drawForEvent() {
    VersionHelper.deprecate(
      "Scheduler",
      "6.0.0",
      "Dependencies.drawForEvent() is no longer needed",
    );
    this.refresh();
  }
  //endregion
  //region Scheduler hooks
  render() {
    this.client.getConfig("svgCanvas");
  }
  //endregion
};
__publicField(Dependencies, "$name", "Dependencies");
/**
 * Fired when dependencies are rendered
 * @on-owner
 * @event dependenciesDrawn
 */
//region Config
__publicField(Dependencies, "configurable", {
  /**
   * The CSS class to add to a dependency line when hovering over it
   * @config {String}
   * @default
   * @private
   */
  overCls: "b-sch-dependency-over",
  /**
   * The CSS class applied to dependency lines
   * @config {String}
   * @default
   * @private
   */
  baseCls: "b-sch-dependency",
  /**
   * The CSS class applied to a too narrow dependency line (to hide markers)
   * @config {String}
   * @default
   * @private
   */
  noMarkerCls: "b-sch-dependency-markerless",
  /**
   * SVG path definition used as marker (arrow head) for the dependency lines.
   * Should fit in a viewBox that is 9 x 6.
   *
   * ```javascript
   * const scheduler = new Scheduler({
   *     features : {
   *         dependencies : {
   *             // Circular marker
   *             markerDef : 'M 2,3 a 3,3 0 1,0 6,0 a 3,3 0 1,0 -6,0'
   *         }
   *     }
   * });
   * ```
   *
   * @config {String}
   * @default 'M3,0 L3,6 L9,3 z'
   */
  markerDef: null,
  /**
   * Radius (in px) used to draw arcs where dependency line segments connect. Specify it to get a rounded look.
   * The radius will during drawing be reduced as needed on a per segment basis to fit lines.
   *
   * ```javascript
   * const scheduler = new Scheduler({
   *     features : {
   *         dependencies : {
   *             // Round the corner where line segments connect, similar to 'border-radius: 5px'
   *             radius : 5
   *         }
   *     }
   * });
   * ```
   *
   * <div class="note">Using a radius slightly degrades dependency rendering performance. If your app displays
   * a lot of dependencies, it might be worth taking this into account when deciding if you want to use radius
   * or not</div>
   *
   * @config {Number}
   */
  radius: null,
  /**
   * Renderer function, supply one if you want to manipulate the {@link DomConfig} object used to draw a
   * dependency line between two assignments.
   *
   * ```javascript
   * const scheduler = new Scheduler({
   *     features : {
   *         dependencies : {
   *             renderer({ domConfig, fromAssignmentRecord : from, toAssignmentRecord : to }) {
   *                 // Add a custom CSS class to dependencies between important assignments
   *                 domConfig.class.important = from.important || to.important;
   *                 domConfig.class.veryImportant = from.important && to.important;
   *             }
   *         }
   *     }
   * }
   * ```
   *
   * @prp {Function}
   * @param {Object} renderData
   * @param {DomConfig} renderData.domConfig that will be used to create the dependency line, can be manipulated by the renderer
   * @param {Scheduler.model.DependencyModel} renderData.dependencyRecord The dependency being rendered
   * @param {Scheduler.model.AssignmentModel} renderData.fromAssignmentRecord Drawing line from this assignment
   * @param {Scheduler.model.AssignmentModel} renderData.toAssignmentRecord Drawing line to this assignment
   * @param {Object[]} renderData.points A collection of points making up the line segments for the dependency line.
   *   Read-only in the renderer, any manipulation should be done to `domConfig`
   * @param {Core.helper.util.Rectangle} renderData.fromBox Bounds for the fromAssignment's element
   * @param {Core.helper.util.Rectangle} renderData.toBox Bounds for the toAssignment's element
   * @param {'top'|'right'|'bottom'|'left'} renderData.fromSide Drawn from this side of the fromAssignment
   * @param {'top'|'right'|'bottom'|'left'} renderData.toSide Drawn to this side of the fromAssignment
   * @returns {void}
   *
   * @category Rendering
   */
  renderer: null,
  /**
   * Specify `true` to highlight incoming and outgoing dependencies when hovering an event.
   * @prp {Boolean}
   */
  highlightDependenciesOnEventHover: null,
  /**
   * Specify `false` to prevent dependencies from being drawn during scroll, for smoother scrolling in schedules
   * with lots of dependencies. Dependencies will be drawn when scrolling stops instead.
   * @prp {Boolean}
   * @default
   */
  drawOnScroll: true,
  /**
   * The clickable/touchable width of the dependency line in pixels. Setting this to a number greater than 1 will
   * draw an invisible but clickable line along the same path as the dependency line, making it easier to click.
   * The tradeoff is that twice as many lines will be drawn, which can affect performance.
   * @prp {Number}
   */
  clickWidth: null,
  /**
   * By default, the refresh of dependencies is buffered by 10 milliseconds so that multiple changes
   * which may cause the dependency lines to become invalid are coalesced into one refresh. This is more
   * efficient, but may mean the dependency lines may lag behind expectations when moving a pointer.
   *
   * Set this to `true` to update dependency lines immediately upon any change which causes them
   * to require an update.
   * @prp {Boolean}
   * @default false
   * @private
   */
  immediateRefresh: null,
  /**
   * *Experimental* - This setting only applies when using dependencies with the nested events feature. In such
   * scenarios, enabling this config will cause the dependency lines to, when the algorithm determines it is
   * possible, be drawn around parent events, instead of through them.
   *
   * {@note}
   * Note that enabling this feature increases the complexity of dependency drawing, and it does have a negative
   * impact on performance.
   * {/@note}
   *
   * @prp {Boolean}
   */
  drawAroundParents: null,
});
__publicField(Dependencies, "delayable", {
  doRefresh: 10,
  rafRefresh: "raf",
});
Dependencies._$name = "Dependencies";
GridFeatureManager.registerFeature(Dependencies, false, [
  "Scheduler",
  "ResourceHistogram",
]);

// ../Scheduler/lib/Scheduler/view/DependencyEditor.js
var DependencyEditor = class extends Popup {
  static get $name() {
    return "DependencyEditor";
  }
  static get defaultConfig() {
    return {
      items: [],
      draggable: {
        handleSelector: ":not(button,.b-field-inner)",
        // blacklist buttons and field inners
      },
      axisLock: "flexible",
    };
  }
  processWidgetConfig(widget) {
    const { dependencyEditFeature } = this;
    if (widget.ref === "lagField" && !dependencyEditFeature.showLagField) {
      return false;
    }
    if (
      widget.ref === "deleteButton" &&
      !dependencyEditFeature.showDeleteButton
    ) {
      return false;
    }
    return super.processWidgetConfig(widget);
  }
  afterShow(...args) {
    const { deleteButton } = this.widgetMap;
    if (deleteButton) {
      deleteButton.hidden = !this.record.isPartOfStore();
    }
    super.afterShow(...args);
  }
  onInternalKeyDown(event) {
    this.trigger("keyDown", { event });
    super.onInternalKeyDown(event);
  }
};
DependencyEditor._$name = "DependencyEditor";

// ../Scheduler/lib/Scheduler/feature/DependencyEdit.js
var DependencyEdit = class extends InstancePlugin {
  //region Config
  static get $name() {
    return "DependencyEdit";
  }
  static get configurable() {
    return {
      /**
       * True to hide this editor if a click is detected outside it (defaults to true)
       * @config {Boolean}
       * @default
       * @category Editor
       */
      autoClose: true,
      /**
       * True to save and close this panel if ENTER is pressed in one of the input fields inside the panel.
       * @config {Boolean}
       * @default
       * @category Editor
       */
      saveAndCloseOnEnter: true,
      /**
       * True to show a delete button in the form.
       * @config {Boolean}
       * @default
       * @category Editor widgets
       */
      showDeleteButton: true,
      /**
       * The event that shall trigger showing the editor. Defaults to `dependencydblclick`, set to empty string or
       * `null` to disable editing of dependencies.
       * @config {String}
       * @default
       * @category Editor
       */
      triggerEvent: "dependencydblclick",
      /**
       * True to show the lag field for the dependency
       * @config {Boolean}
       * @default
       * @category Editor widgets
       */
      showLagField: false,
      dependencyRecord: null,
      /**
       * Default editor configuration, used to configure the Popup.
       * @config {PopupConfig}
       * @category Editor
       */
      editorConfig: {
        title: "L{Edit dependency}",
        localeClass: this,
        closable: true,
        defaults: {
          localeClass: this,
        },
        items: {
          /**
           * Reference to the source task name field
           * @member {Core.widget.DisplayField} fromNameField
           * @readonly
           */
          fromNameField: {
            type: "display",
            weight: 100,
            label: "L{From}",
          },
          /**
           * Reference to the target task name field
           * @member {Core.widget.DisplayField} toNameField
           * @readonly
           */
          toNameField: {
            type: "display",
            weight: 200,
            label: "L{To}",
          },
          /**
           * Reference to the dependency type field
           * @member {Core.widget.Combo} typeField
           * @readonly
           */
          typeField: {
            type: "combo",
            weight: 300,
            label: "L{Type}",
            name: "type",
            editable: false,
            valueField: "id",
            displayField: "name",
            localizeDisplayFields: true,
            buildItems: function () {
              const dialog = this.parent;
              return Object.keys(DependencyModel.Type).map((type) => ({
                id: DependencyModel.Type[type],
                name: dialog.L(type),
                localeKey: type,
              }));
            },
          },
          /**
           * Reference to the lag field
           * @member {Core.widget.DurationField} lagField
           * @readonly
           */
          lagField: {
            type: "duration",
            weight: 400,
            label: "L{Lag}",
            name: "lag",
            allowNegative: true,
            highlightExternalChange: false,
          },
        },
        bbar: {
          defaults: {
            localeClass: this,
          },
          items: {
            foo: {
              type: "widget",
              cls: "b-label-filler",
            },
            /**
             * Reference to the save button, if used
             * @member {Core.widget.Button} saveButton
             * @readonly
             */
            saveButton: {
              color: "b-green",
              text: "L{Save}",
            },
            /**
             * Reference to the delete button, if used
             * @member {Core.widget.Button} deleteButton
             * @readonly
             */
            deleteButton: {
              color: "b-gray",
              text: "L{Delete}",
            },
            /**
             * Reference to the cancel button, if used
             * @member {Core.widget.Button} cancelButton
             * @readonly
             */
            cancelButton: {
              color: "b-gray",
              text: "L{Object.Cancel}",
            },
          },
        },
      },
    };
  }
  //endregion
  //region Init & destroy
  construct(client, config) {
    const me = this;
    client.dependencyEdit = me;
    super.construct(client, config);
    if (!client.features.dependencies) {
      throw new Error(
        "Dependencies feature required when using DependencyEdit",
      );
    }
    me.clientListenersDetacher = client.ion({
      [me.triggerEvent]: me.onActivateEditor,
      thisObj: me,
    });
  }
  doDestroy() {
    var _a4;
    this.clientListenersDetacher();
    (_a4 = this.editor) == null ? void 0 : _a4.destroy();
    super.doDestroy();
  }
  //endregion
  //region Editing
  changeEditorConfig(config) {
    const me = this,
      { autoClose, cls: cls2, client } = me;
    return ObjectHelper.assign(
      {
        owner: client,
        align: "b-t",
        id: `${client.id}-dependency-editor`,
        autoShow: false,
        anchor: true,
        scrollAction: "realign",
        constrainTo: globalThis,
        autoClose,
        cls: cls2,
      },
      config,
    );
  }
  //endregion
  //region Save
  get isValid() {
    return Object.values(this.editor.widgetMap).every((field2) => {
      if (!field2.name || field2.hidden) {
        return true;
      }
      return field2.isValid !== false;
    });
  }
  get values() {
    const values = {};
    this.editor.eachWidget((widget) => {
      if (!widget.name || widget.hidden) return;
      values[widget.name] = widget.value;
    }, true);
    return values;
  }
  /**
   * Template method, intended to be overridden. Called before the dependency record has been updated.
   * @param {Scheduler.model.DependencyModel} dependencyRecord The dependency record
   *
   **/
  onBeforeSave(dependencyRecord) {}
  /**
   * Template method, intended to be overridden. Called after the dependency record has been updated.
   * @param {Scheduler.model.DependencyModel} dependencyRecord The dependency record
   *
   **/
  onAfterSave(dependencyRecord) {}
  /**
   * Updates record being edited with values from the editor
   * @private
   */
  updateRecord(dependencyRecord) {
    const { values } = this;
    if (values.lag) {
      values.lagUnit = values.lag.unit;
      values.lag = values.lag.magnitude;
    }
    if ("type" in values) {
      dependencyRecord.fromSide != null && (values.fromSide = null);
      dependencyRecord.toSide != null && (values.toSide = null);
    }
    ObjectHelper.cleanupProperties(values, true);
    dependencyRecord.set(values);
  }
  //endregion
  //region Events
  onPopupKeyDown({ event }) {
    if (
      event.key === "Enter" &&
      this.saveAndCloseOnEnter &&
      event.target.tagName.toLowerCase() === "input"
    ) {
      event.preventDefault();
      this.onSaveClick();
    }
  }
  onHide() {
    if (!this.isApplyingChanges) {
      this.afterCancel();
    }
  }
  async onSaveClick() {
    const me = this;
    me.isApplyingChanges = true;
    if (await me.save()) {
      me.afterSave();
      await me.editor.hide();
      me.isApplyingChanges = false;
    } else {
      me.isApplyingChanges = false;
    }
  }
  async onDeleteClick() {
    const me = this;
    me.isApplyingChanges = true;
    if (await me.deleteDependency()) {
      me.afterDelete();
    }
    await me.editor.hide();
    me.isApplyingChanges = false;
  }
  onCancelClick() {
    this.editor.hide();
  }
  afterSave() {}
  afterDelete() {}
  afterCancel() {}
  //region Editing
  // Called from editDependency() to actually show the editor
  internalShowEditor(dependencyRecord) {
    const me = this,
      { client, lastPointerDown } = me,
      { dependencies } = client.features,
      editor = me.getEditor(dependencyRecord),
      targetElement =
        (dependencies == null
          ? void 0
          : dependencies.getElementForDependency(dependencyRecord)) ||
        (lastPointerDown == null ? void 0 : lastPointerDown.target) ||
        client.timeAxisSubGridElement,
      targetRect = Rectangle.from(targetElement);
    me.loadRecord(dependencyRecord);
    client.trigger("beforeDependencyEditShow", {
      dependencyEdit: me,
      dependencyRecord,
      editor,
    });
    let alignSpec;
    if (lastPointerDown) {
      Object.defineProperties(lastPointerDown, {
        offsetX: {
          configurable: true,
          value: lastPointerDown.clientX - targetRect.x,
        },
        offsetY: {
          configurable: true,
          value: lastPointerDown.clientY - targetRect.y,
        },
      });
      alignSpec = {
        target: lastPointerDown,
        align: "t50-b0",
      };
    } else {
      alignSpec = {
        target: targetElement,
        align: "c-c",
      };
    }
    const result = editor.showBy(alignSpec),
      labelled = [];
    let labelWidth = 0;
    editor.eachWidget((widget) => {
      const { labelElement, element } = widget;
      if (labelElement) {
        if (
          labelElement.getBoundingClientRect().top <
          element.getBoundingClientRect().top
        ) {
          return false;
        }
        widget.labelWidth = null;
        labelWidth = Math.max(labelWidth, labelElement.offsetWidth);
        labelled.push(widget);
      }
    });
    labelled.forEach((widget) => (widget.labelWidth = labelWidth));
    return result;
  }
  /**
   * Opens a popup to edit the passed dependency.
   * @param {Scheduler.model.DependencyModel} dependencyRecord The dependency to edit
   * @return {Promise} A Promise that yields `true` after the editor is shown
   * or `false` if some application logic vetoed the editing (see `beforeDependencyEdit` in the docs).
   */
  async editDependency(dependencyRecord) {
    const me = this,
      { client } = me;
    if (
      client.readOnly ||
      dependencyRecord.readOnly /**
       * Fires on the owning Scheduler or Gantt widget before an dependency is displayed in the editor.
       * This may be listened for to allow an application to take over dependency editing duties. Return `false` to
       * stop the default editing UI from being shown or a `Promise` yielding `true` or `false` for async vetoing.
       * @event beforeDependencyEdit
       * @on-owner
       * @param {Scheduler.view.Scheduler} source The scheduler or Gantt instance
       * @param {Scheduler.feature.DependencyEdit} dependencyEdit The dependencyEdit feature
       * @param {Scheduler.model.DependencyModel} dependencyRecord The record about to be shown in the editor.
       * @preventable
       * @async
       */ ||
      (await client.trigger("beforeDependencyEdit", {
        dependencyEdit: me,
        dependencyRecord,
      })) === false
    ) {
      return false;
    }
    await this.internalShowEditor(dependencyRecord);
    return true;
  }
  //endregion
  //region Save
  /**
   * Gets an editor instance. Creates on first call, reuses on consecutive
   * @internal
   * @returns {Scheduler.view.DependencyEditor} Editor popup
   */
  getEditor() {
    var _a4, _b, _c;
    const me = this;
    let { editor } = me;
    if (editor) {
      return editor;
    }
    editor = me.editor = DependencyEditor.new(
      {
        dependencyEditFeature: me,
        autoShow: false,
        anchor: true,
        scrollAction: "realign",
        constrainTo: globalThis,
        autoClose: me.autoClose,
        cls: me.cls,
        rootElement: me.client.rootElement,
        internalListeners: {
          keydown: me.onPopupKeyDown,
          hide: me.onHide,
          thisObj: me,
        },
      },
      me.editorConfig,
    );
    if (editor.items.length === 0) {
      console.warn("Editor configured without any `items`");
    }
    editor.eachWidget((widget) => {
      const ref = widget.ref || widget.id;
      if (ref && !me[ref]) {
        me[ref] = widget;
      }
    });
    (_a4 = me.saveButton) == null
      ? void 0
      : _a4.ion({ click: "onSaveClick", thisObj: me });
    (_b = me.deleteButton) == null
      ? void 0
      : _b.ion({ click: "onDeleteClick", thisObj: me });
    (_c = me.cancelButton) == null
      ? void 0
      : _c.ion({ click: "onCancelClick", thisObj: me });
    return me.editor;
  }
  //endregion
  //region Delete
  /**
   * Sets fields values from record being edited
   * @private
   */
  loadRecord(dependency) {
    const me = this;
    me.fromNameField.value = dependency.fromEvent.name;
    me.toNameField.value = dependency.toEvent.name;
    if (me.lagField) {
      me.lagField.value = new Duration(dependency.lag, dependency.lagUnit);
    }
    me.editor.record = me.dependencyRecord = dependency;
  }
  //endregion
  //region Stores
  /**
   * Saves the changes (applies them to record if valid, if invalid editor stays open)
   * @private
   * @fires beforeDependencySave
   * @fires beforeDependencyAdd
   * @fires afterDependencySave
   * @returns {*}
   */
  async save() {
    var _a4;
    const me = this,
      { client, dependencyRecord } = me;
    if (!dependencyRecord || !me.isValid) {
      return;
    }
    const { dependencyStore, values } = me;
    if (
      client.trigger("beforeDependencySave", {
        dependencyRecord,
        values,
      }) !== false
    ) {
      me.onBeforeSave(dependencyRecord);
      me.updateRecord(dependencyRecord);
      if (dependencyStore && !dependencyRecord.stores.length) {
        if (
          client.trigger("beforeDependencyAdd", {
            dependencyRecord,
            dependencyEdit: me,
          }) === false
        ) {
          return;
        }
        dependencyStore.add(dependencyRecord);
      }
      await ((_a4 = client.project) == null ? void 0 : _a4.commitAsync());
      client.trigger("afterDependencySave", { dependencyRecord });
      me.onAfterSave(dependencyRecord);
    }
    return dependencyRecord;
  }
  /**
   * Delete dependency being edited
   * @private
   * @fires beforeDependencyDelete
   */
  async deleteDependency() {
    var _a4;
    const { client, editor, dependencyRecord } = this;
    if (
      client.trigger("beforeDependencyDelete", { dependencyRecord }) !== false
    ) {
      if (editor.containsFocus) {
        editor.revertFocus();
      }
      client.dependencyStore.remove(dependencyRecord);
      await ((_a4 = client.project) == null ? void 0 : _a4.commitAsync());
      return true;
    }
    return false;
  }
  get dependencyStore() {
    return this.client.dependencyStore;
  }
  //endregion
  //region Events
  onActivateEditor({ dependency, event }) {
    if (!this.disabled) {
      this.lastPointerDown = event;
      this.editDependency(dependency);
    }
  }
  //endregion
};
DependencyEdit._$name = "DependencyEdit";
GridFeatureManager.registerFeature(DependencyEdit, false);

// ../Scheduler/lib/Scheduler/feature/ScheduleContext.js
var ScheduleContext = class extends InstancePlugin.mixin(Delayable_default) {
  static get $name() {
    return "ScheduleContext";
  }
  /**
   * The contextual information about which cell was clicked on and highlighted.
   *
   * When the {@link Scheduler.view.Scheduler#property-viewPreset} is changed (such as when zooming)
   * the context is cleared and the highlight is removed.
   *
   * @member {Object} context
   * @property {Scheduler.view.TimelineBase} context.source The owning Scheduler
   * @property {Date} context.date Date at mouse position
   * @property {Scheduler.model.TimeSpan} context.tick A record which encapsulates the time axis tick clicked on.
   * @property {Number} context.tickIndex The index of the time axis tick clicked on.
   * @property {Date} context.tickStartDate The start date of the current time axis tick
   * @property {Date} context.tickEndDate The end date of the current time axis tick
   * @property {Grid.row.Row} context.row Clicked row (in horizontal mode only)
   * @property {Number} context.index Index of clicked resource
   * @property {Scheduler.model.ResourceModel} context.resourceRecord Resource record
   * @property {MouseEvent} context.event Browser event
   */
  construct(client, config) {
    super.construct(client, config);
    const { triggerEvent } = this,
      listeners = {
        datachange: "syncContextElement",
        timeaxisviewmodelupdate: "onTimeAxisViewModelUpdate",
        presetchange: "clearContext",
        thisObj: this,
      };
    if (triggerEvent === "mouseover") {
      listeners.timelineContextChange = "onTimelineContextChange";
    } else {
      if (triggerEvent === "click" || triggerEvent === "mousedown") {
        listeners.schedulecontextmenu = "onScheduleContextGesture";
      }
      Object.assign(listeners, {
        [`schedule${triggerEvent}`]: "onScheduleContextGesture",
        [`event${triggerEvent}`]: "onScheduleContextGesture",
        ...listeners,
      });
    }
    client.ion(listeners);
    client.rowManager.ion({
      rowheight: "syncContextElement",
      thisObj: this,
    });
  }
  changeTriggerEvent(triggerEvent) {
    if (triggerEvent === "hover" || triggerEvent === "mousemove") {
      triggerEvent = "mouseover";
    }
    return triggerEvent;
  }
  get element() {
    return (
      this._element ||
      (this._element = DomHelper.createElement({
        parent: this.client.timeAxisSubGridElement,
        className: "b-schedule-selected-tick",
      }))
    );
  }
  // Handle the Client's own timelineContextChange event which it maintains on mousemove
  onTimelineContextChange({ context }) {
    this.context = context;
  }
  // Handle the scheduleclick or eventclick Scheduler events if we re not using mouseover
  onScheduleContextGesture(context) {
    this.context = context;
  }
  onTimeAxisViewModelUpdate({ source: timeAxisViewModel }) {
    var _a4;
    if (
      timeAxisViewModel.timeAxis.includes(
        (_a4 = this.context) == null ? void 0 : _a4.tick,
      )
    ) {
      this.syncContextElement();
    } else {
      this.clearContext();
    }
  }
  clearContext() {
    this.context = null;
  }
  updateContext(context, oldContext) {
    this.syncContextElement();
  }
  syncContextElement() {
    if (this.context && this.enabled) {
      const me = this,
        { client, element, context, renderer } = me,
        { isVertical } = client,
        { style } = element,
        row = isVertical
          ? client.rowManager.rows[0]
          : client.getRowFor(context.resourceRecord);
      if (row) {
        const { tickStartDate, tickEndDate, resourceRecord } = context,
          renderData = client.currentOrientation.getTimeSpanRenderData(
            {
              startDate: tickStartDate,
              endDate: tickEndDate,
              startDateMS: tickStartDate.getTime(),
              endDateMS: tickEndDate.getTime(),
            },
            resourceRecord,
          );
        let top, width, height;
        if (isVertical) {
          top = renderData.top;
          width = renderData.resourceWidth;
          height = renderData.height;
        } else {
          top = row.top;
          width = renderData.width;
          height = row.height;
        }
        style.display = "";
        style.width = `${width}px`;
        style.height = `${height}px`;
        DomHelper.setTranslateXY(element, renderData.left, top);
        context.index = row.index;
        element.innerHTML = "";
        renderer && me.callback(renderer, me, [context, element]);
      } else {
        style.display = "none";
      }
    } else {
      this.element.style.display = "none";
    }
  }
};
__publicField(ScheduleContext, "delayable", {
  syncContextElement: "raf",
});
__publicField(ScheduleContext, "configurable", {
  /**
   * The pointer event type to use to update the context. May be `'hover'` to highlight the
   * tick context when moving the mouse across the timeline.
   * @config {'click'|'hover'|'contextmenu'|'mousedown'}
   * @default
   */
  triggerEvent: "click",
  /**
   * A function (or the name of a function) which may mutate the contents of the context overlay
   * element which tracks the active resource/tick context.
   *
   * @config {String|Function}
   * @param {TimelineContext} context The context being highlighted.
   * @param {HTMLElement} element The context highlight element. This will be empty each time.
   * @returns {void}
   */
  renderer: null,
  /**
   * The active context.
   * @member {TimelineContext} timelineContext
   * @readonly
   */
  context: {
    $config: {
      // Reject non-changes so that when using mousemove, we only update the context
      // when it changes.
      equal(c1, c2) {
        return (
          (c1 == null ? void 0 : c1.index) ===
            (c2 == null ? void 0 : c2.index) &&
          (c1 == null ? void 0 : c1.tickParentIndex) ===
            (c2 == null ? void 0 : c2.tickParentIndex) &&
          !(
            ((c1 == null ? void 0 : c1.tickStartDate) || 0) -
            ((c2 == null ? void 0 : c2.tickStartDate) || 0)
          )
        );
      },
    },
  },
});
ScheduleContext.featureClass = "b-scheduler-context";
ScheduleContext._$name = "ScheduleContext";
GridFeatureManager.registerFeature(ScheduleContext, false, ["Scheduler"]);

// ../Scheduler/lib/Scheduler/feature/EventCopyPaste.js
var actions6 = {
  cut: 1,
  copy: 1,
  paste: 1,
};
var EventCopyPaste = class extends CopyPasteBase.mixin(
  AttachToProjectMixin_default,
) {
  constructor() {
    super(...arguments);
    // Used in events to separate events from different features from each other
    __publicField(this, "entityName", "event");
  }
  construct(scheduler, config) {
    super.construct(scheduler, config);
    scheduler.ion({
      eventClick: "onEventClick",
      scheduleClick: "onScheduleClick",
      projectChange: () => {
        this.clearClipboard();
        this._cellClickedContext = null;
      },
      thisObj: this,
    });
  }
  get scheduler() {
    return this.client;
  }
  attachToEventStore(eventStore) {
    super.attachToEventStore(eventStore);
    delete this._eventClickedContext;
  }
  onEventDataGenerated(eventData) {
    const { assignmentRecord } = eventData;
    if (assignmentRecord) {
      eventData.cls["b-cut-item"] = assignmentRecord.meta.isCut;
    }
  }
  onEventClick(context) {
    this._cellClickedContext = null;
    this._eventClickedContext = context;
  }
  onScheduleClick(context) {
    this._cellClickedContext = context;
    this._eventClickedContext = null;
  }
  isActionAvailable({ event, actionName }) {
    var _a4, _b;
    if (actions6[actionName]) {
      return (
        !this.disabled &&
        globalThis.getSelection().toString().length === 0 &&
        !((_a4 = this.client.features.cellEdit) == null
          ? void 0
          : _a4.isEditing) &&
        Boolean(event.target.closest(".b-timeaxissubgrid")) &&
        !((_b = this.client.focusedCell) == null ? void 0 : _b.isSpecialRow)
      );
    }
  }
  async copy() {
    await this.copyEvents();
  }
  async cut() {
    await this.copyEvents(void 0, true);
  }
  async paste() {
    await this.pasteEvents();
  }
  /**
   * Copy events (when using single assignment mode) or assignments (when using multi assignment mode) to clipboard to
   * paste later
   * @fires beforeCopy
   * @fires copy
   * @param {Scheduler.model.EventModel[]|Scheduler.model.AssignmentModel[]} [records] Pass records to copy them,
   * leave out to copying current selection
   * @param {Boolean} [isCut] Copies by default, pass `true` to cut instead
   * @category Edit
   * @on-owner
   */
  async copyEvents(
    records = this.scheduler.selectedAssignments,
    isCut = false,
  ) {
    const me = this,
      { scheduler } = me;
    if (scheduler.splitFrom) {
      return scheduler.splitFrom.features.eventCopyPaste.copyEvents(
        records,
        isCut,
      );
    }
    if (!(records == null ? void 0 : records.length)) {
      return;
    }
    let assignmentRecords = records.slice();
    if (records[0].isEventModel) {
      assignmentRecords = records.map((r) => r.assignments).flat();
    }
    if (isCut) {
      assignmentRecords = assignmentRecords.filter((a) => !a.event.readOnly);
    }
    const eventRecords = assignmentRecords.map((a) => a.event);
    if (!assignmentRecords.length || scheduler.readOnly) {
      return;
    }
    await me.writeToClipboard({ assignmentRecords, eventRecords }, isCut);
    scheduler.trigger("copy", {
      assignmentRecords,
      eventRecords,
      isCut,
      entityName: me.entityName,
    });
    scheduler.refreshWithTransition();
    me._focusedEventOnCopy = me._eventClickedContext;
  }
  async beforeCopy({ data: { assignmentRecords, eventRecords }, isCut }) {
    return await this.scheduler.trigger("beforeCopy", {
      assignmentRecords,
      eventRecords,
      isCut,
      entityName: this.entityName,
    });
  }
  // Called from Clipboardable when cutData changes
  handleCutData({ source }) {
    var _a4;
    const me = this;
    if (source !== me && ((_a4 = me.cutData) == null ? void 0 : _a4.length)) {
      const { assignmentRecords, eventRecords } = me.cutData[0];
      if (assignmentRecords == null ? void 0 : assignmentRecords.length) {
        me.scheduler.assignmentStore.remove(assignmentRecords);
      }
      if (eventRecords == null ? void 0 : eventRecords.length) {
        me.scheduler.eventStore.remove(eventRecords);
      }
    }
  }
  /**
   * Called from Clipboardable after writing a non-string value to the clipboard
   * @param eventRecords
   * @returns {string}
   * @private
   */
  stringConverter({ eventRecords }) {
    const rows = [];
    for (const event of eventRecords) {
      rows.push(
        this.eventToStringFields
          .map((field2) => {
            const value = event[field2];
            if (value instanceof Date) {
              return DateHelper.format(value, this.dateFormat);
            }
            return value;
          })
          .join("	"),
      );
    }
    return rows.join("\n");
  }
  // Called from Clipboardable for each cut out record
  setIsCut({ assignmentRecords }, isCut) {
    assignmentRecords.forEach((assignment) => {
      assignment.meta.isCut = isCut;
    });
    this.scheduler.refreshWithTransition();
  }
  /**
   * Paste events or assignments to specified date and resource
   * @fires beforePaste
   * @fires paste
   * @param {Date} [date] Date where the events or assignments will be pasted
   * @param {Scheduler.model.ResourceModel} [resourceRecord] Resource to assign the pasted events or assignments to
   * @category Edit
   * @on-owner
   */
  async pasteEvents(date, resourceRecord) {
    var _a4;
    const me = this,
      { scheduler } = me;
    if (scheduler.splitFrom) {
      return scheduler.splitFrom.features.eventCopyPaste.pasteEvents(
        date,
        resourceRecord,
      );
    }
    const { entityName, isCut, _cellClickedContext, _eventClickedContext } = me,
      { eventStore, assignmentStore } = scheduler;
    if (arguments.length === 0) {
      if (_cellClickedContext) {
        date = _cellClickedContext.date;
        resourceRecord = _cellClickedContext.resourceRecord;
      } else if (me._focusedEventOnCopy !== _eventClickedContext) {
        date = _eventClickedContext.eventRecord.startDate;
        resourceRecord = _eventClickedContext.resourceRecord;
      }
    }
    if (resourceRecord) {
      resourceRecord = resourceRecord.$original;
    }
    const clipboardData = await me.readFromClipboard({ resourceRecord, date });
    if (
      !((_a4 =
        clipboardData == null ? void 0 : clipboardData.assignmentRecords) ==
      null
        ? void 0
        : _a4.length)
    ) {
      return;
    }
    const { assignmentRecords, eventRecords } = clipboardData;
    let toFocus = null;
    const pastedEvents = /* @__PURE__ */ new Set(),
      pastedEventRecords = [];
    for (const assignmentRecord of assignmentRecords) {
      let { event } = assignmentRecord;
      const targetResourceRecord = resourceRecord || assignmentRecord.resource,
        targetDate = date || assignmentRecord.event.startDate;
      if (pastedEvents.has(event)) {
        if (isCut) {
          assignmentRecord.remove();
        }
        continue;
      }
      pastedEvents.add(event);
      if (isCut) {
        assignmentRecord.meta.isCut = false;
        assignmentRecord.resource = targetResourceRecord;
        toFocus = assignmentRecord;
      } else if (
        !eventStore.usesResourceIds &&
        (eventStore.usesSingleAssignment || me.copyPasteAction === "clone")
      ) {
        event = event.copy();
        event.name = me.generateNewName(event);
        eventStore.add(event);
        event.assign(targetResourceRecord);
        toFocus = assignmentStore.last;
      } else if (!event.resources.includes(targetResourceRecord)) {
        const newAssignmentRecord = assignmentRecord.copy();
        newAssignmentRecord.resource = targetResourceRecord;
        [toFocus] = assignmentStore.add(newAssignmentRecord);
      }
      event.startDate = targetDate;
      if (event.constraintDate) {
        event.constraintDate = null;
      }
      pastedEventRecords.push(event);
    }
    scheduler.trigger("paste", {
      assignmentRecords,
      pastedEventRecords,
      eventRecords,
      resourceRecord,
      date,
      isCut,
      entityName,
    });
    const detacher2 = scheduler.ion({
      renderEvent({ assignmentRecord }) {
        if (assignmentRecord === toFocus) {
          scheduler.navigateTo(assignmentRecord, { scrollIntoView: false });
          detacher2();
        }
      },
    });
    if (isCut) {
      await me.clearClipboard();
    }
  }
  // Called from Clipboardable before finishing the internal clipboard read
  async beforePaste({
    data: { assignmentRecords, eventRecords },
    resourceRecord,
    isCut,
    date,
  }) {
    const { scheduler } = this,
      eventData = {
        assignmentRecords,
        eventRecords,
        resourceRecord: resourceRecord || assignmentRecords[0].resource,
        date,
        isCut,
        entityName: this.entityName,
      };
    let reason;
    if (resourceRecord == null ? void 0 : resourceRecord.readOnly) {
      reason = "resourceReadOnly";
    }
    if (!scheduler.allowOverlap) {
      const pasteWouldResultInOverlap = assignmentRecords.some(
        (assignmentRecord) =>
          !scheduler.isDateRangeAvailable(
            assignmentRecord.event.startDate,
            assignmentRecord.event.endDate,
            isCut ? assignmentRecord.event : null,
            assignmentRecord.resource,
          ),
      );
      if (pasteWouldResultInOverlap) {
        reason = "overlappingEvents";
      }
    }
    if (reason) {
      scheduler.trigger("pasteNotAllowed", {
        ...eventData,
        reason,
      });
      return false;
    }
    return await this.scheduler.trigger("beforePaste", eventData);
  }
  /**
   * Called from Clipboardable after reading from clipboard, and it is determined that the clipboard data is
   * "external"
   * @param json
   * @returns {Object}
   * @private
   */
  stringParser(clipboardData) {
    const { eventStore, assignmentStore } = this.scheduler,
      { modifiedRecords: eventRecords } = this.setFromStringData(
        clipboardData,
        true,
        eventStore,
        this.eventToStringFields,
      ),
      assignmentRecords = [];
    for (const event of eventRecords) {
      const assignment = new assignmentStore.modelClass({ eventId: event.id });
      assignment.event = event;
      assignmentRecords.push(assignment);
    }
    return { eventRecords, assignmentRecords };
  }
  populateEventMenu({ assignmentRecord, items: items2 }) {
    const me = this,
      { scheduler } = me;
    if (!scheduler.readOnly) {
      items2.copyEvent = {
        text: "L{copyEvent}",
        localeClass: me,
        icon: "b-icon b-icon-copy",
        weight: 110,
        onItem: () => {
          const assignments = scheduler.isAssignmentSelected(assignmentRecord)
            ? scheduler.selectedAssignments
            : [assignmentRecord];
          me.copyEvents(assignments);
        },
      };
      items2.cutEvent = {
        text: "L{cutEvent}",
        localeClass: me,
        icon: "b-icon b-icon-cut",
        weight: 120,
        disabled: assignmentRecord.event.readOnly,
        onItem: () => {
          const assignments = scheduler.isAssignmentSelected(assignmentRecord)
            ? scheduler.selectedAssignments
            : [assignmentRecord];
          me.copyEvents(assignments, true);
        },
      };
    }
  }
  populateScheduleMenu({ items: items2, resourceRecord }) {
    const me = this,
      { scheduler } = me;
    if (!scheduler.readOnly && me.hasClipboardData() !== false) {
      items2.pasteEvent = {
        text: "L{pasteEvent}",
        localeClass: me,
        icon: "b-icon b-icon-paste",
        disabled:
          scheduler.resourceStore.count === 0 || resourceRecord.readOnly,
        weight: 110,
        onItem: ({ date, resourceRecord: resourceRecord2 }) => {
          me.pasteEvents(
            date,
            resourceRecord2,
            scheduler.getRowFor(resourceRecord2),
          );
        },
      };
    }
  }
  /**
   * A method used to generate the name for a copy pasted record. By defaults appends "- 2", "- 3" as a suffix.
   *
   * @param {Scheduler.model.EventModel} eventRecord The new eventRecord being pasted
   * @returns {String}
   */
  generateNewName(eventRecord) {
    const originalName = eventRecord.getValue(this.nameField);
    let counter3 = 2;
    while (
      this.client.eventStore.findRecord(
        this.nameField,
        `${originalName} - ${counter3}`,
      )
    ) {
      counter3++;
    }
    return `${originalName} - ${counter3}`;
  }
};
__publicField(EventCopyPaste, "$name", "EventCopyPaste");
__publicField(EventCopyPaste, "pluginConfig", {
  assign: ["copyEvents", "pasteEvents"],
  chain: ["populateEventMenu", "populateScheduleMenu", "onEventDataGenerated"],
});
__publicField(EventCopyPaste, "configurable", {
  /**
   * The field to use as the name field when updating the name of copied records
   * @config {String}
   * @default
   */
  nameField: "name",
  /**
   * How to handle a copy paste operation when the host uses multi assignment. Either:
   *
   * - `'clone'`  - The default, clone the copied event, assigning the clone to the target resource.
   * - `'assign'` - Add an assignment for the existing event to the target resource.
   *
   * For single assignment mode, it always uses the `'clone'` behaviour.
   *
   * @config {'clone'|'assign'}
   * @default
   */
  copyPasteAction: "clone",
  /**
   * When copying events (or assignments), data will be sent to the clipboard as a tab (`\t`) and new-line (`\n`)
   * separated string with field values for fields present in this config (in specified order). The default
   * included fields are (in this order):
   * * name
   * * startDate
   * * endDate
   * * duration
   * * durationUnit
   * * allDay
   * To override, provide your own array of fields:
   * ```javascript
   * new Scheduler({
   *     features : {
   *         eventCopyPaste : {
   *             eventToStringFields : [
   *                'name',
   *                'startDate',
   *                'endDate',
   *                'percentDone'
   *             ]
   *         }
   *     }
   * });
   * ```
   * <div class="note">Please note that this config is both used for **converting** events to a string value and
   * is also used to **parse** a string value to events.</div>
   * @config {Array<String>}
   */
  eventToStringFields: [
    "name",
    "startDate",
    "endDate",
    "duration",
    "durationUnit",
    "allDay",
  ],
});
EventCopyPaste.featureClass = "b-event-copypaste";
EventCopyPaste._$name = "EventCopyPaste";
GridFeatureManager.registerFeature(EventCopyPaste, true, "Scheduler");

// ../Scheduler/lib/Scheduler/feature/EventDrag.js
var EventDrag = class extends DragBase {
  //region Config
  static get $name() {
    return "EventDrag";
  }
  static get configurable() {
    return {
      /**
       * Template used to generate drag tooltip contents.
       * ```javascript
       * const scheduler = new Scheduler({
       *     features : {
       *         eventDrag : {
       *             dragTipTemplate({eventRecord, startText}) {
       *                 return `${eventRecord.name}: ${startText}`
       *             }
       *         }
       *     }
       * });
       * ```
       * @config {Function} tooltipTemplate
       * @param {Object} data Tooltip data
       * @param {Scheduler.model.EventModel} data.eventRecord
       * @param {Boolean} data.valid Currently over a valid drop target or not
       * @param {Date} data.startDate New start date
       * @param {Date} data.endDate New end date
       * @returns {String}
       */
      /**
       * Set to true to only allow dragging events within the same resource.
       * @member {Boolean} constrainDragToResource
       */
      /**
       * Set to true to only allow dragging events within the same resource.
       * @config {Boolean}
       * @default
       */
      constrainDragToResource: false,
      /**
       * Set to true to only allow dragging events to different resources, and disallow rescheduling by dragging.
       * @member {Boolean} constrainDragToTimeSlot
       */
      /**
       * Set to true to only allow dragging events to different resources, and disallow rescheduling by dragging.
       * @config {Boolean}
       * @default
       */
      constrainDragToTimeSlot: false,
      /**
       * A CSS selector specifying elements outside the scheduler element which are valid drop targets.
       * @config {String}
       */
      externalDropTargetSelector: null,
      /**
       * An empty function by default, but provided so that you can perform custom validation on the item being
       * dragged. This function is called during the drag and drop process and also after the drop is made.
       * Return `true` if the new position is valid, `false` to prevent the drag.
       *
       * ```javascript
       * features : {
       *     eventDrag : {
       *         validatorFn({ eventRecords, newResource }) {
       *             const
       *                 task  = eventRecords[0],
       *                 valid = newResource.role === task.resource.role;
       *
       *             return {
       *                 valid   : newResource.role === task.resource.role,
       *                 message : valid ? '' : 'Resource role does not match required role for this task'
       *             };
       *         }
       *     }
       * }
       * ```
       * @param {Object} context A drag drop context object
       * @param {Date} context.startDate New start date
       * @param {Date} context.endDate New end date
       * @param {Scheduler.model.AssignmentModel[]} context.assignmentRecords Assignment records which were dragged
       * @param {Scheduler.model.EventModel[]} context.eventRecords Event records which were dragged
       * @param {Scheduler.model.ResourceModel} context.newResource New resource record
       * @param {Scheduler.model.EventModel} context.targetEventRecord Currently hovering this event record
       * @param {Event} event The event object
       * @returns {Boolean|Object} `true` if this validation passes, `false` if it does not.
       *
       * Or an object with 2 properties: `valid` -  Boolean `true`/`false` depending on validity,
       * and `message` - String with a custom error message to display when invalid.
       * @config {Function}
       */
      validatorFn: (context, event) => {},
      /**
       * The `this` reference for the validatorFn
       * @config {Object}
       */
      validatorFnThisObj: null,
      /**
       * When the host Scheduler is `{@link Scheduler.view.mixin.EventSelection#config-multiEventSelect}: true`
       * then, there are two modes of dragging *within the same Scheduler*.
       *
       * Non unified means that all selected events are dragged by the same number of resource rows.
       *
       * Unified means that all selected events are collected together and dragged as one, and are all dropped
       * on the same targeted resource row at the same targeted time.
       * @member {Boolean} unifiedDrag
       */
      /**
       * When the host Scheduler is `{@link Scheduler.view.mixin.EventSelection#config-multiEventSelect}: true`
       * then, there are two modes of dragging *within the same Scheduler*.
       *
       * Non unified means that all selected events are dragged by the same number of resource rows.
       *
       * Unified means that all selected events are collected together and dragged as one, and are all dropped
       * on the same targeted resource row at the same targeted time.
       * @config {Boolean}
       * @default false
       */
      unifiedDrag: null,
      /**
       * A hook that allows manipulating the position the drag proxy snaps to. Manipulate the `snapTo` property
       * to alter snap position.
       *
       * ```javascript
       * const scheduler = new Scheduler({
       *     features : {
       *         eventDrag : {
       *             snapToPosition({ eventRecord, snapTo }) {
       *                 if (eventRecord.late) {
       *                     snapTo.x = 400;
       *                 }
       *             }
       *         }
       *     }
       * });
       * ```
       *
       * @config {Function}
       * @param {Object} context
       * @param {Scheduler.model.AssignmentModel} context.assignmentRecord Dragged assignment
       * @param {Scheduler.model.EventModel} context.eventRecord Dragged event
       * @param {Scheduler.model.ResourceModel} context.resourceRecord Currently over this resource
       * @param {Date} context.startDate Start date for current position
       * @param {Date} context.endDate End date for current position
       * @param {Object} context.snapTo
       * @param {Number} context.snapTo.x X to snap to
       * @param {Number} context.snapTo.y Y to snap to
       * @returns {void}
       */
      snapToPosition: null,
      /**
       * A modifier key (CTRL, SHIFT, ALT, META) that when pressed will copy an event instead of moving it. Set to
       * empty string to disable copying
       * @prp {'CTRL'|'ALT'|'SHIFT'|'META'|''}
       * @default
       */
      copyKey: "SHIFT",
      /**
       * Event can be copied two ways: either by adding new assignment to an existing event ('assignment'), or
       * by copying the event itself ('event'). 'auto' mode will pick 'event' for a single-assignment mode (when
       * event has `resourceId` field) and 'assignment' mode otherwise.
       * @prp {'auto'|'assignment'|'event'}
       * @default
       */
      copyMode: "auto",
      /**
       * Mode of the current drag drop operation.
       * @member {'move'|'copy'}
       * @readonly
       */
      mode: "move",
      capitalizedEventName: null,
    };
  }
  afterConstruct() {
    this.capitalizedEventName =
      this.capitalizedEventName || this.client.capitalizedEventName;
    super.afterConstruct(...arguments);
  }
  //endregion
  changeMode(value) {
    const { dragData, copyMode } = this;
    if (
      (copyMode === "event" ||
        copyMode === "auto" ||
        (copyMode === "assignment" &&
          !this.scheduler.eventStore.usesSingleAssignment)) &&
      (!dragData || dragData.eventRecords.every((r) => !r.isRecurring))
    ) {
      return value;
    }
  }
  updateMode(mode) {
    if (this.dragData) {
      if (mode === "copy") {
        this.setCopying();
      } else {
        this.setMoving();
      }
      this.client.trigger("eventDragModeChange", { mode });
    }
  }
  setCopying() {
    const { dragData } = this;
    if (!dragData) {
      return;
    }
    if (!dragData.eventBarCopies.some((el) => el.isConnected)) {
      dragData.eventBarCopies.forEach((el) => {
        el.classList.add("b-drag-proxy-copy");
        el.classList.remove("b-hidden");
        dragData.context.grabbedParent.appendChild(el);
        el.retainElement = true;
      });
    } else {
      dragData.eventBarCopies.forEach((el) => {
        el.classList.remove("b-hidden");
      });
    }
  }
  setMoving() {
    const { dragData } = this;
    if (!dragData) {
      return;
    }
    dragData.eventBarCopies.forEach((el) => {
      el.classList.add("b-hidden");
    });
  }
  //region Events
  /**
   * This event is fired on the owning Scheduler after the event drag operation completes, but before changing any data.
   * It allows implementer to use asynchronous validation/finalization by setting `context.async = true`
   * in the listener, for example, to show a confirmation popup, make async data request etc.
   * In such case, implementer need to call the `context.finalize()` method manually:
   *
   * ```javascript
   *  scheduler.on('beforeeventdropfinalize', ({ context }) => {
   *      context.async = true;
   *      setTimeout(() => {
   *          // `true` to perform the drop, `false` to ignore it
   *          context.finalize(true);
   *      }, 1000);
   *  })
   * ```
   *
   * For synchronous one-time validation, simply set `context.valid` to true or false.
   * ```javascript
   *  scheduler.on('beforeeventdropfinalize', ({ context }) => {
   *      context.valid = false;
   *  })
   * ```
   * @event beforeEventDropFinalize
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Object} context
   * @param {DropData} context.dropData Information about the drop points for dragged events/assignments.
   * @param {Boolean} context.async Set to `true` to not finalize the drag-drop operation immediately (e.g. to wait for user confirmation)
   * @param {Scheduler.model.EventModel[]} context.eventRecords Event records being dragged
   * @param {Scheduler.model.AssignmentModel[]} context.assignmentRecords Assignment records being dragged
   * @param {Scheduler.model.EventModel} context.targetEventRecord Event record for drop target
   * @param {Scheduler.model.ResourceModel} context.newResource Resource record for drop target
   * @param {Boolean} context.valid Set this to `false` to abort the drop immediately.
   * @param {Function} context.finalize Call this method after an **async** finalization flow, to finalize the drag-drop operation. This method accepts one
   * argument: pass `true` to update records, or `false` to ignore changes
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler after event drop
   * @event afterEventDrop
   * @on-owner
   * @param {Scheduler.view.Scheduler} source
   * @param {Scheduler.model.AssignmentModel[]} assignmentRecords
   * @param {Scheduler.model.EventModel[]} eventRecords
   * @param {Boolean} valid
   * @param {Object} context
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler when an event is dropped
   * @event eventDrop
   * @on-owner
   * @param {Scheduler.view.Scheduler} source
   * @param {Scheduler.model.EventModel[]} eventRecords
   * @param {Scheduler.model.AssignmentModel[]} assignmentRecords
   * @param {HTMLElement} externalDropTarget The HTML element dropped upon, if drop happened on a valid external drop target
   * @param {Boolean} isCopy
   * @param {Object} context
   * @param {Scheduler.model.EventModel} context.targetEventRecord Event record for drop target
   * @param {Scheduler.model.ResourceModel} context.newResource Resource record for drop target
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler before event dragging starts. Return `false` to prevent the action.
   * @event beforeEventDrag
   * @on-owner
   * @preventable
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.EventModel} eventRecord Event record the drag starts from
   * @param {Scheduler.model.ResourceModel} resourceRecord Resource record the drag starts from
   * @param {Scheduler.model.EventModel[]} eventRecords Event records being dragged
   * @param {Scheduler.model.AssignmentModel[]} assignmentRecords Assignment records being dragged
   * @param {MouseEvent} event Browser event DEPRECATED (replaced by domEvent)
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler when event dragging starts
   * @event eventDragStart
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.ResourceModel} resourceRecord Resource record the drag starts from
   * @param {Scheduler.model.EventModel[]} eventRecords Event records being dragged
   * @param {Scheduler.model.AssignmentModel[]} assignmentRecords Assignment records being dragged
   * @param {MouseEvent} event Browser event DEPRECATED (replaced by domEvent)
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler when event is dragged
   * @event eventDrag
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.EventModel[]} eventRecords Event records being dragged
   * @param {Scheduler.model.AssignmentModel[]} assignmentRecords Assignment records being dragged
   * @param {Date} startDate Start date for the current location
   * @param {Date} endDate End date for the current location
   * @param {Scheduler.model.ResourceModel} resourceRecord Resource record the drag started from
   * @param {Scheduler.model.ResourceModel} newResource Resource at the current location
   * @param {Object} context
   * @param {Boolean} context.valid Set this to `false` to signal that the current drop position is invalid.
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler after an event drag operation has been aborted
   * @event eventDragAbort
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.EventModel[]} eventRecords Event records being dragged
   * @param {Scheduler.model.AssignmentModel[]} assignmentRecords Assignment records being dragged
   * @param {MouseEvent} domEvent Browser event
   */
  /**
   * Fired on the owning Scheduler after an event drag operation regardless of the operation being cancelled or not
   * @event eventDragReset
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   */
  //endregion
  //region Data layer
  // Deprecated. Use this.client instead
  get scheduler() {
    return this.client;
  }
  //endregion
  //#region Drag lifecycle
  onAfterDragStart(event) {
    const me = this,
      {
        context: { element },
      } = event;
    super.onAfterDragStart(event);
    me.handleKeyDownOrMove(event.event);
    me.keyEventDetacher = EventHelper.on({
      // In case we drag event between scheduler focused event gets moved and focus
      // moves to the body. We only need to read the key from this event
      element: DomHelper.getRootElement(element),
      keydown: me.handleKeyDownOrMove,
      keyup: me.handleKeyUp,
      thisObj: me,
    });
  }
  onDragReset(event) {
    var _a4;
    super.onDragReset(event);
    (_a4 = this.keyEventDetacher) == null ? void 0 : _a4.call(this);
    this.mode = "move";
  }
  onDrop(event) {
    var _a4;
    (_a4 = this.dragData.eventBarCopies) == null
      ? void 0
      : _a4.forEach((el) => el.remove());
    return super.onDrop(event);
  }
  //#endregion
  //region Drag events
  getDraggableElement(el) {
    return el == null ? void 0 : el.closest(this.drag.targetSelector);
  }
  resolveEventRecord(eventElement, client = this.client) {
    return client.resolveEventRecord(eventElement);
  }
  isElementDraggable(el, event) {
    var _a4;
    const me = this,
      { client } = me,
      eventElement = me.getDraggableElement(el);
    if (!eventElement || me.disabled || client.readOnly) {
      return false;
    }
    if (el.matches('[class$="-handle"]')) {
      return false;
    }
    const eventRecord = me.resolveEventRecord(eventElement, client);
    if (!eventRecord || !eventRecord.isDraggable || eventRecord.readOnly) {
      return false;
    }
    const prevented =
      ((_a4 = client[`is${me.capitalizedEventName}ElementDraggable`]) == null
        ? void 0
        : _a4.call(client, eventElement, eventRecord, el, event)) === false;
    return !prevented;
  }
  getTriggerParams(dragData) {
    const {
      assignmentRecords,
      eventRecords,
      resourceRecord,
      browserEvent: domEvent,
    } = dragData;
    return {
      // `context` is now private, but used in WebSocketHelper
      context: dragData,
      eventRecords,
      resourceRecord,
      assignmentRecords,
      event: domEvent,
      // Deprecated, remove on  6.0?
      domEvent,
    };
  }
  getGroupedToStoreResources(dragData) {
    if (dragData.resourcesInStore) {
      return dragData.resourcesInStore;
    }
    const fromScheduler = this.client,
      fromResourceStore = fromScheduler.isVertical
        ? fromScheduler.resourceStore
        : fromScheduler.store;
    return (dragData.resourcesInStore = [
      ...new Set(fromResourceStore.getAllDataRecords().map((r) => r.$original)),
    ].filter((r) => r.isLeaf));
  }
  getIndexDiff(dragData) {
    const me = this,
      fromScheduler = me.client,
      toScheduler = me.currentOverClient,
      isCrossScheduler = fromScheduler !== toScheduler,
      { isVertical } = toScheduler,
      fromResourceStore = fromScheduler.isVertical
        ? fromScheduler.resourceStore
        : fromScheduler.store,
      toResourceStore = isVertical
        ? toScheduler.resourceStore
        : toScheduler.store,
      { resourceRecord: fromResource, newResource: toResource } = dragData;
    let indexDiff;
    if (isCrossScheduler) {
      indexDiff =
        toResourceStore.indexOf(toResource) -
        fromResourceStore.indexOf(fromResource.$original);
    } else if (me.constainDragToResource) {
      indexDiff = 0;
    } else if (isVertical && toResourceStore.isGrouped) {
      const resourcesInStore = me.getGroupedToStoreResources(dragData);
      indexDiff =
        resourcesInStore.indexOf(fromResource.$original) -
        resourcesInStore.indexOf(toResource);
    } else {
      indexDiff =
        fromResourceStore.indexOf(fromResource.$original) -
        fromResourceStore.indexOf(toResource);
    }
    return indexDiff;
  }
  getNewResource(dragData, originalResourceRecord, indexDiff) {
    const me = this,
      fromScheduler = me.client,
      toScheduler = me.currentOverClient,
      isCrossScheduler = fromScheduler !== toScheduler,
      { isVertical } = toScheduler,
      fromResourceStore = fromScheduler.isVertical
        ? fromScheduler.resourceStore
        : fromScheduler.store,
      toResourceStore = isVertical
        ? toScheduler.resourceStore
        : toScheduler.store;
    let { newResource } = dragData;
    if (!isCrossScheduler) {
      if (indexDiff !== 0) {
        let newIndex;
        if (isVertical && toResourceStore.isGrouped) {
          const resourcesInStore = me.getGroupedToStoreResources(dragData);
          newIndex = Math.max(
            Math.min(
              resourcesInStore.indexOf(originalResourceRecord) - indexDiff,
              resourcesInStore.length - 1,
            ),
            0,
          );
          newResource = resourcesInStore[newIndex];
        } else {
          newIndex = Math.max(
            Math.min(
              fromResourceStore.indexOf(originalResourceRecord) - indexDiff,
              fromResourceStore.count - 1,
            ),
            0,
          );
          newResource = fromResourceStore.getAt(newIndex);
          if (newResource.isSpecialRow) {
            newResource =
              fromResourceStore.getNext(newResource, false, true) ||
              fromResourceStore.getPrevious(newResource, false, true);
          }
        }
        newResource = newResource == null ? void 0 : newResource.$original;
      } else {
        newResource = originalResourceRecord;
      }
    } else {
      const draggedEventResourceIndex = fromResourceStore.indexOf(
        originalResourceRecord,
      );
      newResource =
        toResourceStore.getAt(draggedEventResourceIndex + indexDiff) ||
        newResource;
    }
    return newResource;
  }
  getDropData(dragData) {
    const indexDiff = this.getIndexDiff(dragData);
    return {
      events: dragData.eventRecords.map((eventRecord) => {
        return {
          eventRecord,
          ...this.getEventNewStartEndDates(eventRecord, dragData.timeDiff),
        };
      }),
      assignments: dragData.assignmentRecords.map((assignmentRecord) => {
        return {
          assignmentRecord,
          resourceRecord: this.getNewResource(
            dragData,
            assignmentRecord.resource,
            indexDiff,
          ),
        };
      }),
    };
  }
  triggerBeforeEventDropFinalize(eventType, eventData, client) {
    eventData.context.dropData = this.getDropData(eventData.context);
    super.triggerBeforeEventDropFinalize(eventType, eventData, client);
  }
  triggerBeforeEventDrag(eventType, event) {
    return this.client.trigger(eventType, event);
  }
  triggerEventDrag(dragData, start) {
    this.client.trigger(
      "eventDrag",
      Object.assign(this.getTriggerParams(dragData), {
        startDate: dragData.startDate,
        endDate: dragData.endDate,
        newResource: dragData.newResource,
      }),
    );
  }
  triggerDragStart(dragData) {
    this.client.navigator.skipNextClick = true;
    this.client.trigger("eventDragStart", this.getTriggerParams(dragData));
  }
  triggerDragAbort(dragData) {
    this.client.trigger("eventDragAbort", this.getTriggerParams(dragData));
  }
  triggerDragAbortFinalized(dragData) {
    this.client.trigger(
      "eventDragAbortFinalized",
      this.getTriggerParams(dragData),
    );
  }
  triggerAfterDrop(dragData, valid) {
    const me = this;
    me.currentOverClient.trigger(
      "afterEventDrop",
      Object.assign(me.getTriggerParams(dragData), {
        valid,
      }),
    );
    if (!valid) {
      const { assignmentStore, eventStore } = me.client,
        needRefresh = me.dragData.initialAssignmentsState.find(
          ({ resource, assignment }, i) => {
            var _a4;
            return (
              !assignmentStore.includes(assignment) ||
              !eventStore.includes(assignment.event) ||
              resource.id !==
                ((_a4 = me.dragData.assignmentRecords[i]) == null
                  ? void 0
                  : _a4.resourceId)
            );
          },
        );
      if (needRefresh) {
        me.client.refresh();
      }
    }
    me.client.setTimeout(() => (me.client.navigator.skipNextClick = false), 10);
  }
  handleKeyDownOrMove(event) {
    var _a4, _b;
    if (this.mode !== "copy") {
      if (
        (event.key &&
          EventHelper.specialKeyFromEventKey(event.key) ===
            ((_a4 = this.copyKey) == null ? void 0 : _a4.toLowerCase())) ||
        event[`${(_b = this.copyKey) == null ? void 0 : _b.toLowerCase()}Key`]
      ) {
        this.mode = "copy";
      }
    }
  }
  handleKeyUp(event) {
    if (
      EventHelper.specialKeyFromEventKey(event.key) ===
      this.copyKey.toLowerCase()
    ) {
      this.mode = "move";
    }
  }
  //endregion
  //region Finalization & validation
  /**
   * Checks if an event can be dropped on the specified position.
   * @private
   * @returns {Boolean} Valid (true) or invalid (false)
   */
  isValidDrop(dragData) {
    const { newResource, resourceRecord, browserEvent } = dragData,
      sourceRecord = dragData.draggedEntities[0],
      { target } = browserEvent;
    if (!newResource) {
      return !this.constrainDragToTimeline && this.externalDropTargetSelector
        ? Boolean(target.closest(this.externalDropTargetSelector))
        : false;
    }
    if (newResource.isSpecialRow || newResource.readOnly) {
      return false;
    }
    if (resourceRecord.$original !== newResource) {
      return !sourceRecord.event.resources.includes(newResource);
    }
    return true;
  }
  checkDragValidity(dragData, event) {
    var _a4, _b, _c;
    const me = this,
      scheduler = me.currentOverClient;
    let result;
    if ((_a4 = dragData.newResource) == null ? void 0 : _a4.readOnly) {
      return false;
    }
    if (
      !scheduler.allowOverlap &&
      !scheduler.isDateRangeAvailable(
        dragData.startDate,
        dragData.endDate,
        dragData.draggedEntities[0],
        dragData.newResource,
      )
    ) {
      result = {
        valid: false,
        message: me.L("L{eventOverlapsExisting}"),
      };
    } else {
      result = me.validatorFn.call(
        me.validatorFnThisObj || me,
        dragData,
        event,
      );
    }
    if (!result || result.valid) {
      result =
        (_c =
          (_b = scheduler["checkEventDragValidity"]) == null
            ? void 0
            : _b.call(scheduler, dragData, event)) != null
          ? _c
          : result;
    }
    return result;
  }
  //endregion
  //region Update records
  /**
   * Update events being dragged.
   * @private
   * @param context Drag data.
   */
  async updateRecords(context) {
    const me = this,
      fromScheduler = me.client,
      toScheduler = me.currentOverClient,
      copyKeyPressed = me.mode === "copy",
      { draggedEntities, timeDiff, initialAssignmentsState } = context,
      originalStartDate = initialAssignmentsState[0].startDate,
      droppedStartDate = me.adjustStartDate(originalStartDate, timeDiff);
    let result;
    if (!context.externalDropTarget) {
      if (
        !toScheduler.timeAxis.timeSpanInAxis(
          droppedStartDate,
          DateHelper.add(
            droppedStartDate,
            draggedEntities[0].event.durationMS,
            "ms",
          ),
        )
      ) {
        context.valid = false;
      }
      if (context.valid) {
        fromScheduler.eventStore.suspendAutoCommit();
        toScheduler.eventStore.suspendAutoCommit();
        result = await me.updateAssignments(
          fromScheduler,
          toScheduler,
          context,
          copyKeyPressed,
        );
        fromScheduler.eventStore.resumeAutoCommit();
        toScheduler.eventStore.resumeAutoCommit();
      }
    }
    if (context.valid) {
      toScheduler.trigger(
        "eventDrop",
        Object.assign(me.getTriggerParams(context), {
          isCopy: copyKeyPressed,
          copyMode: me.copyMode,
          domEvent: context.browserEvent,
          targetEventRecord: context.targetEventRecord,
          targetResourceRecord: context.newResource,
          externalDropTarget: context.externalDropTarget,
        }),
      );
    }
    return result;
  }
  /**
   * Update assignments being dragged
   * @private
   */
  async updateAssignments(fromScheduler, toScheduler, context, copy) {
    var _a4, _b, _c;
    const me = this,
      { copyMode } = me,
      isCrossScheduler = fromScheduler !== toScheduler,
      { isVertical } = toScheduler,
      { assignmentStore: fromAssignmentStore, eventStore: fromEventStore } =
        fromScheduler,
      { assignmentStore: toAssignmentStore, eventStore: toEventStore } =
        toScheduler,
      fromResourceStore = fromScheduler.isVertical
        ? fromScheduler.resourceStore
        : fromScheduler.store,
      {
        eventRecords,
        assignmentRecords,
        timeDiff,
        initialAssignmentsState,
        newResource: toResource,
      } = context,
      { unifiedDrag } = me,
      useSingleAssignment =
        toEventStore.usesSingleAssignment ||
        (toEventStore.usesSingleAssignment !== false &&
          fromEventStore.usesSingleAssignment),
      effectiveCopyMode =
        copyMode === "event"
          ? "event"
          : copyMode === "assignment"
            ? "assignment"
            : useSingleAssignment
              ? "event"
              : "assignment",
      event1Date = me.adjustStartDate(
        assignmentRecords[0].event.startDate,
        timeDiff,
      ),
      eventsToAdd = [],
      eventsToRemove = [],
      assignmentsToAdd = [],
      assignmentsToRemove = [],
      eventsToCheck = [],
      eventsToBatch = /* @__PURE__ */ new Set();
    fromScheduler.suspendRefresh();
    toScheduler.suspendRefresh();
    let updated = false,
      updatedEvent = false,
      indexDiff = me.getIndexDiff(context);
    if (isVertical) {
      eventRecords.forEach((draggedEvent, i) => {
        const eventBar = context.eventBarEls[i];
        delete draggedEvent.instanceMeta(fromScheduler).hasTemporaryDragElement;
        if (eventBar.dataset.transient) {
          eventBar.remove();
        }
      });
    }
    const eventBarEls = context.eventBarEls.slice(),
      addedEvents = [],
      copiedAssignmentsMap = {};
    for (let i = 0; i < assignmentRecords.length; i++) {
      const originalAssignment = assignmentRecords[i];
      let draggedEvent = originalAssignment.event,
        draggedAssignment;
      if (copy) {
        draggedAssignment = originalAssignment.copy();
        copiedAssignmentsMap[originalAssignment.id] = draggedAssignment;
      } else {
        draggedAssignment = originalAssignment;
      }
      if (
        !draggedAssignment.isOccurrenceAssignment &&
        (!fromAssignmentStore.includes(originalAssignment) ||
          !fromEventStore.includes(draggedEvent))
      ) {
        eventBarEls[i].remove();
        eventBarEls.splice(i, 1);
        assignmentRecords.splice(i, 1);
        i--;
        continue;
      }
      const initialState = initialAssignmentsState[i],
        originalEventRecord = draggedEvent,
        originalStartDate = initialState.startDate,
        originalResourceRecord = initialState.resource,
        newStartDate = this.constrainDragToTimeSlot
          ? originalStartDate
          : unifiedDrag
            ? event1Date
            : me.adjustStartDate(originalStartDate, timeDiff);
      if (fromAssignmentStore !== toAssignmentStore) {
        const keepEvent = originalEventRecord.assignments.length > 1 || copy;
        let newAssignment;
        if (copy) {
          newAssignment = draggedAssignment;
        } else {
          newAssignment = draggedAssignment.copy();
          copiedAssignmentsMap[draggedAssignment.id] = newAssignment;
        }
        if (newAssignment.event && !useSingleAssignment) {
          newAssignment.event = newAssignment.event.id;
          newAssignment.resource = newAssignment.resource.id;
        }
        if (!copy) {
          assignmentsToRemove.push(draggedAssignment);
        }
        if (!keepEvent) {
          eventsToRemove.push(originalEventRecord);
        }
        if (
          (copy &&
            (copyMode === "event" ||
              (copyMode === "auto" && toEventStore.usesSingleAssignment))) ||
          !toEventStore.getById(originalEventRecord.id)
        ) {
          draggedEvent = toEventStore.createRecord({
            ...originalEventRecord.data,
            children:
              (_a4 = originalEventRecord.children) == null
                ? void 0
                : _a4.map((child) => child.copy()),
            // If we're copying the event (not making new assignment to existing), we need to generate
            // phantom id to link event to the assignment record
            id:
              copy && (copyMode === "event" || copyMode === "auto")
                ? void 0
                : originalEventRecord.id,
            // Engine gets mad if not nulled
            calendar: null,
          });
          newAssignment.set({
            eventId: draggedEvent.id,
            event: draggedEvent,
          });
          eventsToAdd.push(draggedEvent);
        }
        if (!useSingleAssignment) {
          assignmentsToAdd.push(newAssignment);
        }
        draggedAssignment = newAssignment;
      }
      let newResource = toResource,
        reassignedFrom = null;
      if (!unifiedDrag) {
        newResource =
          me.getNewResource(context, originalResourceRecord, indexDiff) ||
          toResource;
      }
      const isCrossResource =
        draggedAssignment.resourceId !== newResource.$original.id;
      if (isCrossResource) {
        reassignedFrom = fromResourceStore.getById(
          draggedAssignment.resourceId,
        );
        if (copy && fromAssignmentStore === toAssignmentStore) {
          draggedAssignment.setData({
            resource: null,
            resourceId: null,
          });
          draggedAssignment.resource = newResource;
          draggedAssignment.event = toEventStore.getById(
            draggedAssignment.eventId,
          );
          const shouldCopyEvent =
            copyMode === "event" ||
            (fromEventStore.usesSingleAssignment && copyMode === "auto");
          if (shouldCopyEvent) {
            draggedEvent = draggedEvent.copy();
            draggedEvent.meta.endDateCached = me.adjustStartDate(
              draggedEvent.endDate,
              timeDiff,
            );
            draggedEvent.endDate = null;
            draggedAssignment.event = draggedEvent;
            if (toEventStore.usesSingleAssignment) {
              draggedEvent.resource = newResource;
              draggedEvent.resourceId = newResource.id;
            }
          }
          if (
            !toAssignmentStore.find(
              (a) =>
                a.eventId === draggedAssignment.eventId &&
                a.resourceId === draggedAssignment.resourceId,
            ) &&
            !assignmentsToAdd.find(
              (r) =>
                r.eventId === draggedAssignment.eventId &&
                r.resourceId === draggedAssignment.resourceId,
            )
          ) {
            shouldCopyEvent && eventsToAdd.push(draggedEvent);
            assignmentsToAdd.push(draggedAssignment);
          }
        } else {
          draggedAssignment.resource = newResource;
        }
        draggedEvent.isEvent && eventsToBatch.add(draggedEvent);
        updated = true;
        if (draggedEvent.isOccurrence) {
          draggedEvent.set("newResource", newResource);
        }
        if (isCrossScheduler && useSingleAssignment) {
          draggedEvent.resourceId = newResource.id;
        }
      } else {
        if (
          copy &&
          (copyMode === "event" ||
            (copyMode === "auto" && fromEventStore.usesSingleAssignment)) &&
          !eventsToAdd.includes(draggedEvent)
        ) {
          draggedEvent = draggedEvent.copy();
          draggedEvent.meta.endDateCached = me.adjustStartDate(
            draggedEvent.endDate,
            timeDiff,
          );
          draggedEvent.endDate = null;
          eventsToAdd.push(draggedEvent);
          draggedAssignment.event = draggedEvent;
          if (toEventStore.usesSingleAssignment) {
            draggedEvent.set({
              resource: newResource,
              resourceId: newResource.id,
            });
          }
          assignmentsToAdd.push(draggedAssignment);
        }
      }
      if (
        !eventsToCheck.find((ev) => ev.draggedEvent === draggedEvent) &&
        !DateHelper.isEqual(draggedEvent.startDate, newStartDate)
      ) {
        while (!draggedEvent.isOccurrence && draggedEvent.isBatchUpdating) {
          draggedEvent.endBatch(true);
        }
        const shouldKeepStartDate =
          copy &&
          !isCrossScheduler &&
          !useSingleAssignment &&
          effectiveCopyMode === "assignment" &&
          isCrossResource;
        if (!shouldKeepStartDate) {
          draggedEvent.startDate = newStartDate;
          eventsToCheck.push({ draggedEvent, originalStartDate });
        }
        draggedEvent.isEvent && eventsToBatch.add(draggedEvent);
        updatedEvent = true;
      }
      toScheduler.processEventDrop({
        eventRecord: draggedEvent,
        resourceRecord: newResource,
        element:
          i === 0
            ? context.context.element
            : context.context.relatedElements[i - 1],
        context,
        toScheduler,
        reassignedFrom,
        eventsToAdd,
        addedEvents,
        draggedAssignment,
      });
      toScheduler.trigger("processEventDrop", {
        originalAssignment,
        draggedAssignment,
        context,
        copyMode,
        isCopy: copy,
      });
    }
    fromAssignmentStore.remove(assignmentsToRemove);
    fromEventStore.remove(eventsToRemove);
    toAssignmentStore.add(assignmentsToAdd);
    if (copy && fromAssignmentStore === toAssignmentStore) {
      const { syncIdMap } = fromScheduler.foregroundCanvas;
      Object.entries(copiedAssignmentsMap).forEach(
        ([originalId, cloneRecord]) => {
          const element = syncIdMap[originalId];
          delete syncIdMap[originalId];
          syncIdMap[cloneRecord.id] = element;
        },
      );
    }
    eventsToAdd.length && addedEvents.push(...toEventStore.add(eventsToAdd));
    addedEvents == null
      ? void 0
      : addedEvents.forEach((added) => eventsToBatch.add(added));
    if (
      assignmentsToRemove.length ||
      eventsToRemove.length ||
      assignmentsToAdd.length ||
      eventsToAdd.length
    ) {
      updated = true;
    }
    if (updated || updatedEvent) {
      if (!me.constrainDragToTimeline) {
        for (let i = 0; i < assignmentRecords.length; i++) {
          const assignmentRecord =
              copiedAssignmentsMap[assignmentRecords[i].id] ||
              assignmentRecords[i],
            originalDraggedEvent = assignmentRecord.event,
            draggedEvent =
              (addedEvents == null
                ? void 0
                : addedEvents.find((r) => r.id === originalDraggedEvent.id)) ||
              originalDraggedEvent,
            eventBar = context.eventBarEls[i],
            element =
              i === 0
                ? context.context.element
                : context.context.relatedElements[i - 1],
            inTimeAxis = toScheduler.isInTimeAxis(draggedEvent);
          delete draggedEvent.meta.endDateCached;
          if (!copy) {
            DomSync.removeChild(eventBar.parentElement, eventBar);
          }
          if (
            draggedEvent.resource &&
            (isVertical ||
              toScheduler.rowManager.getRowFor(draggedEvent.resource)) &&
            inTimeAxis
          ) {
            if (!draggedEvent.parent || draggedEvent.parent.isRoot) {
              const elRect = Rectangle.from(
                element,
                toScheduler.foregroundCanvas,
                true,
              );
              DomHelper.setTopLeft(element, elRect.y, elRect.x);
              DomSync.addChild(
                toScheduler.foregroundCanvas,
                element,
                draggedEvent.assignments[0].id,
              );
              isCrossScheduler &&
                toScheduler.processCrossSchedulerEventDrop({
                  eventRecord: draggedEvent,
                  toScheduler,
                });
            }
            element.classList.remove(
              "b-sch-event-hover",
              "b-active",
              "b-drag-proxy",
              "b-dragging",
            );
            element.retainElement = false;
          }
        }
      }
      useSingleAssignment &&
        eventsToBatch.forEach((eventRecord) => eventRecord.beginBatch());
      const toProject =
          (_b = toEventStore.$master.project) != null
            ? _b
            : toScheduler.project,
        fromProject =
          (_c = fromEventStore.$master.project) != null
            ? _c
            : fromScheduler.project;
      await Promise.all([
        toProject !== fromProject ? toProject.commitAsync() : null,
        fromProject.commitAsync(),
      ]);
      useSingleAssignment &&
        eventsToBatch.forEach((eventRecord) =>
          eventRecord.endBatch(false, true),
        );
    }
    if (!updated) {
      updated = eventsToCheck.some(
        ({ draggedEvent, originalStartDate }) =>
          !DateHelper.isEqual(draggedEvent.startDate, originalStartDate),
      );
    }
    toScheduler.resumeRefresh(false);
    fromScheduler.resumeRefresh(false);
    if (assignmentRecords.length > 0) {
      if (!updated) {
        context.valid = false;
      } else {
        eventBarEls.forEach((el) => delete el.lastDomConfig);
        toScheduler.refreshWithTransition();
        if (isCrossScheduler) {
          fromScheduler.refreshWithTransition();
          toScheduler.selectedEvents = addedEvents;
        }
      }
    }
  }
  //endregion
  //region Drag data
  getProductDragContext(dragData) {
    const me = this,
      { currentOverClient: scheduler } = me,
      target = dragData.browserEvent.target,
      previousResolvedResource =
        dragData.newResource || dragData.resourceRecord,
      previousTargetEventRecord = dragData.targetEventRecord;
    let targetEventRecord = scheduler
        ? me.resolveEventRecord(target, scheduler)
        : null,
      newResource,
      externalDropTarget;
    if (dragData.eventRecords.includes(targetEventRecord)) {
      targetEventRecord = null;
    }
    if (me.constrainDragToResource) {
      newResource = dragData.resourceRecord;
    } else if (!me.constrainDragToTimeline) {
      newResource = me.resolveResource();
    } else if (scheduler) {
      newResource =
        me.resolveResource() || dragData.newResource || dragData.resourceRecord;
    }
    const { assignmentRecords, eventRecords } = dragData,
      isOverNewResource = previousResolvedResource !== newResource;
    let valid = Boolean(newResource && !newResource.isSpecialRow);
    if (!newResource && me.externalDropTargetSelector) {
      externalDropTarget = target.closest(me.externalDropTargetSelector);
      valid = Boolean(externalDropTarget);
    }
    return {
      valid,
      externalDropTarget,
      eventRecords,
      assignmentRecords,
      newResource,
      targetEventRecord,
      dirty:
        isOverNewResource || targetEventRecord !== previousTargetEventRecord,
      proxyElements: [
        dragData.context.element,
        ...(dragData.context.relatedElements || []),
      ],
    };
  }
  getMinimalDragData(info) {
    const me = this,
      { scheduler } = me,
      element = me.getElementFromContext(info),
      eventRecord = me.resolveEventRecord(element, scheduler),
      resourceRecord = scheduler.resolveResourceRecord(element),
      assignmentRecord = scheduler.resolveAssignmentRecord(element);
    let assignmentRecords = assignmentRecord ? [assignmentRecord] : [];
    if (
      assignmentRecord &&
      (scheduler.isAssignmentSelected(assignmentRecords[0]) ||
        (me.drag.startEvent.ctrlKey && scheduler.multiEventSelect))
    ) {
      assignmentRecords.push.apply(
        assignmentRecords,
        me.getRelatedRecords(assignmentRecord),
      );
    }
    assignmentRecords = assignmentRecords.filter((assignment) =>
      scheduler.resourceStore.isAvailable(assignment.resource),
    );
    const eventRecords = [
      ...new Set(assignmentRecords.map((assignment) => assignment.event)),
    ];
    return {
      eventRecord,
      resourceRecord,
      assignmentRecord,
      eventRecords,
      assignmentRecords,
    };
  }
  setupProductDragData(info) {
    var _a4;
    const me = this,
      { scheduler } = me,
      element = me.getElementFromContext(info),
      { eventRecord, resourceRecord, assignmentRecord, assignmentRecords } =
        me.getMinimalDragData(info),
      eventBarEls = [];
    if (me.constrainDragToResource && !resourceRecord) {
      throw new Error(
        "Resource could not be resolved for event: " + eventRecord.id,
      );
    }
    let dateConstraints;
    if (me.constrainDragToTimeline) {
      dateConstraints =
        (_a4 = me.getDateConstraints) == null
          ? void 0
          : _a4.call(me, resourceRecord, eventRecord);
      const constrainRectangle = (me.constrainRectangle =
          me.getConstrainingRectangle(
            dateConstraints,
            resourceRecord,
            eventRecord,
          )),
        eventRegion = Rectangle.from(element, scheduler.timeAxisSubGridElement);
      super.setupConstraints(
        constrainRectangle,
        eventRegion,
        scheduler.timeAxisViewModel.snapPixelAmount,
        Boolean(dateConstraints.start),
      );
    }
    assignmentRecords.forEach((assignment) => {
      let eventBarEl = scheduler.getElementFromAssignmentRecord(
        assignment,
        true,
      );
      if (!eventBarEl) {
        eventBarEl = scheduler.currentOrientation.addTemporaryDragElement(
          assignment.event,
          assignment.resource,
        );
      }
      eventBarEls.push(eventBarEl);
    });
    return {
      record: assignmentRecord,
      draggedEntities: assignmentRecords,
      dateConstraints: (
        dateConstraints == null ? void 0 : dateConstraints.start
      )
        ? dateConstraints
        : null,
      // Create copies of the elements
      eventBarCopies: eventBarEls.map((el) => me.createProxy(el)),
      eventBarEls,
    };
  }
  getDateConstraints(resourceRecord, eventRecord) {
    var _a4;
    const { scheduler } = this,
      externalDateConstraints =
        (_a4 = scheduler.getDateConstraints) == null
          ? void 0
          : _a4.call(scheduler, resourceRecord, eventRecord);
    let minDate, maxDate;
    if (this.constrainDragToTimeSlot) {
      minDate = eventRecord.startDate;
      maxDate = eventRecord.endDate;
    } else if (externalDateConstraints) {
      minDate = externalDateConstraints.start;
      maxDate = externalDateConstraints.end;
    }
    return {
      start: minDate,
      end: maxDate,
    };
  }
  getConstrainingRectangle(dateRange, resourceRecord, eventRecord) {
    return this.scheduler.getScheduleRegion(
      this.constrainDragToResource && resourceRecord,
      eventRecord,
      true,
      dateRange && {
        start: dateRange.start,
        end: dateRange.end,
      },
    );
  }
  /**
   * Initializes drag data (dates, constraints, dragged events etc). Called when drag starts.
   * @private
   * @param info
   * @returns {*}
   */
  getDragData(info) {
    const dragData = this.getMinimalDragData(info) || {};
    return {
      ...super.getDragData(info),
      ...dragData,
      initialAssignmentsState: dragData.assignmentRecords.map((assignment) => ({
        startDate: assignment.event.startDate,
        resource: assignment.resource,
        assignment,
      })),
    };
  }
  /**
   * Provide your custom implementation of this to allow additional selected records to be dragged together with the original one.
   * @param {Scheduler.model.AssignmentModel} assignmentRecord The assignment about to be dragged
   * @returns {Scheduler.model.AssignmentModel[]} An array of assignment records to drag together with the original
   */
  getRelatedRecords(assignmentRecord) {
    return this.scheduler.selectedAssignments.filter(
      (selectedRecord) =>
        selectedRecord !== assignmentRecord &&
        !selectedRecord.resource.readOnly &&
        selectedRecord.event.isDraggable,
    );
  }
  /**
   * Get correct axis coordinate depending on schedulers mode (horizontal -> x, vertical -> y). Also takes milestone
   * layout into account.
   * @private
   * @param {Scheduler.model.EventModel} eventRecord Record being dragged
   * @param {HTMLElement} element Element being dragged
   * @param {Number[]} coord XY coordinates
   * @returns {Number|Number[]} X,Y or XY
   */
  getCoordinate(eventRecord, element, coord) {
    const scheduler = this.currentOverClient;
    if (scheduler.isHorizontal) {
      let x = coord[0];
      if (
        scheduler.milestoneLayoutMode !== "default" &&
        eventRecord.isMilestone
      ) {
        switch (scheduler.milestoneAlign) {
          case "center":
            x += element.offsetWidth / 2;
            break;
          case "end":
            x += element.offsetWidth;
            break;
        }
      }
      return x;
    } else {
      let y = coord[1];
      if (
        scheduler.milestoneLayoutMode !== "default" &&
        eventRecord.isMilestone
      ) {
        switch (scheduler.milestoneAlign) {
          case "center":
            y += element.offsetHeight / 2;
            break;
          case "end":
            y += element.offsetHeight;
            break;
        }
      }
      return y;
    }
  }
  /**
   * Get resource record occluded by the drag proxy.
   * @private
   * @returns {Scheduler.model.ResourceModel}
   */
  resolveResource() {
    const me = this,
      client = me.currentOverClient,
      { isHorizontal } = client,
      { context, browserEvent, dragProxy } = me.dragData,
      element = dragProxy || context.element,
      pageRect = Rectangle.from(element, null, true),
      y =
        client.isVertical || me.unifiedDrag
          ? context.clientY
          : pageRect.center.y,
      localRect = Rectangle.from(element, client.timeAxisSubGridElement, true),
      { x: lx, y: ly } = localRect.center;
    let resource = null,
      isInsideClientEl;
    if (browserEvent.touches) {
      isInsideClientEl = Rectangle.from(client.element).contains(
        Point.from(browserEvent, true),
      );
    } else {
      isInsideClientEl = client.element.contains(
        me.getMouseMoveEventTarget(browserEvent),
      );
    }
    if (isInsideClientEl) {
      if (isHorizontal) {
        const row = client.rowManager.getRowAt(y);
        resource = row && client.store.getAt(row.dataIndex);
      } else {
        resource = client.resolveResourceRecord(
          client.timeAxisSubGridElement.querySelector(".b-sch-timeaxis-cell"),
          [lx, ly],
        );
      }
    }
    return resource == null ? void 0 : resource.$original;
  }
  //endregion
  //region Other stuff
  adjustStartDate(startDate, timeDiff) {
    const scheduler = this.currentOverClient;
    startDate = scheduler.timeAxis.roundDate(
      new Date(startDate - 0 + timeDiff),
      scheduler.snapRelativeToEventStartDate ? startDate : false,
    );
    return this.constrainStartDate(startDate);
  }
  getRecordElement(assignmentRecord) {
    return this.client.getElementFromAssignmentRecord(assignmentRecord, true);
  }
  // Used by the Dependencies feature to draw lines to the drag proxy instead of the original event element
  getProxyElement(assignmentRecord) {
    var _a4;
    const { dragData } = this;
    if (
      this.isDragging &&
      ((_a4 = dragData == null ? void 0 : dragData.proxyElements) == null
        ? void 0
        : _a4.length)
    ) {
      const index = dragData.assignmentRecords.indexOf(assignmentRecord);
      if (index >= 0) {
        return dragData.proxyElements[index];
      }
    }
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
