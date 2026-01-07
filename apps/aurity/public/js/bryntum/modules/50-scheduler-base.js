};
var SchedulerBase = class extends TimelineBase.mixin(
  CrudManagerView_default,
  Describable_default,
  SchedulerDom_default,
  SchedulerDomEvents_default,
  SchedulerStores_default,
  SchedulerScroll_default,
  SchedulerState_default,
  SchedulerEventRendering_default,
  SchedulerRegions_default,
  EventSelection_default,
  EventNavigation_default,
  CurrentConfig_default,
  TransactionalFeatureMixin_default,
) {
  constructor() {
    super(...arguments);
    __publicField(this, "timeCellSelector", ".b-sch-timeaxis-cell");
    __publicField(
      this,
      "resourceTimeRangeSelector",
      ".b-sch-resourcetimerange",
    );
  }
  static get defaultConfig() {
    return {
      /**
       * Scheduler mode. Supported values: horizontal, vertical
       * @config {'horizontal'|'vertical'} mode
       * @default
       * @category Common
       */
      mode: "horizontal",
      /**
       * CSS class to add to rendered events
       * @config {String}
       * @category CSS
       * @private
       * @default
       */
      eventCls: "b-sch-event",
      /**
       * CSS class to add to cells in the timeaxis column
       * @config {String}
       * @category CSS
       * @private
       * @default
       */
      timeCellCls: "b-sch-timeaxis-cell",
      /**
       * A CSS class to apply to each event in the view on mouseover (defaults to 'b-sch-event-hover').
       * @config {String}
       * @default
       * @category CSS
       * @private
       */
      overScheduledEventClass: "b-sch-event-hover",
      /**
       * Set to `false` if you don't want to allow events overlapping times for any one resource (defaults to `true`).
       * <div class="note">Note that toggling this at runtime won't affect already overlapping events.</div>
       *
       * @prp {Boolean}
       * @default
       * @category Scheduled events
       */
      allowOverlap: true,
      /**
       * The height in pixels of Scheduler rows.
       * @config {Number}
       * @default
       * @category Common
       */
      rowHeight: 60,
      /**
       * Scheduler overrides Grids default implementation of {@link Grid.view.GridBase#config-getRowHeight} to
       * pre-calculate row heights based on events in the rows.
       *
       * The amount of rows that are pre-calculated is limited for performance reasons. The limit is configurable
       * by specifying the {@link Scheduler.view.SchedulerBase#config-preCalculateHeightLimit} config.
       *
       * The results of the calculation are cached internally.
       *
       * @config {Function} getRowHeight
       * @param {Scheduler.model.ResourceModel} getRowHeight.record Resource record to determine row height for
       * @returns {Number} Desired row height
       * @category Layout
       */
      /**
       * Maximum number of resources for which height is pre-calculated. If you have many events per
       * resource you might want to lower this number to gain some initial rendering performance.
       *
       * Specify a falsy value to opt out of row height pre-calculation.
       *
       * @config {Number}
       * @default
       * @category Layout
       */
      preCalculateHeightLimit: 1e4,
      crudManagerClass: CrudManager,
      // Skip live redraw of events while dragging RegionResize splitter if too many events are rendered in DOM
      liveRedrawWhileMovingSplitterThreshold: 100,
      testConfig: {
        loadMaskError: {
          autoClose: 10,
          showDelay: 0,
        },
      },
    };
  }
  //endregion
  //region Store & model docs
  // Documented here instead of in SchedulerStores since SchedulerPro uses different types
  // Configs
  /**
   * Inline events, will be loaded into an internally created EventStore.
   * @config {Scheduler.model.EventModel[]|Scheduler.model.EventModelConfig[]} events
   * @category Data
   */
  /**
   * The {@link Scheduler.data.EventStore} holding the events to be rendered into the scheduler (required).
   * @config {Scheduler.data.EventStore|Scheduler.data.EventStoreConfig} eventStore
   * @category Data
   */
  /**
   * Inline resources, will be loaded into an internally created ResourceStore.
   * @config {Scheduler.model.ResourceModel[]|Scheduler.model.ResourceModelConfig[]} resources
   * @category Data
   */
  /**
   * The {@link Scheduler.data.ResourceStore} holding the resources to be rendered into the scheduler (required).
   * @config {Scheduler.data.ResourceStore|Scheduler.data.ResourceStoreConfig} resourceStore
   * @category Data
   */
  /**
   * Inline assignments, will be loaded into an internally created AssignmentStore.
   * @config {Scheduler.model.AssignmentModel[]|Object[]} assignments
   * @category Data
   */
  /**
   * The optional {@link Scheduler.data.AssignmentStore}, holding assignments between resources and events.
   * Required for multi assignments.
   * @config {Scheduler.data.AssignmentStore|Scheduler.data.AssignmentStoreConfig} assignmentStore
   * @category Data
   */
  /**
   * Inline dependencies, will be loaded into an internally created DependencyStore.
   * @config {Scheduler.model.DependencyModel[]|Scheduler.model.DependencyModelConfig[]} dependencies
   * @category Data
   */
  /**
   * The optional {@link Scheduler.data.DependencyStore}.
   * @config {Scheduler.data.DependencyStore|Scheduler.model.DependencyStoreConfig} dependencyStore
   * @category Data
   */
  // Properties
  /**
   * Get/set events, applies to the backing project's EventStore.
   * @member {Scheduler.model.EventModel[]} events
   * @accepts {Scheduler.model.EventModel[]|Scheduler.model.EventModelConfig[]}
   * @category Data
   */
  /**
   * Get/set the event store instance of the backing project.
   * @member {Scheduler.data.EventStore} eventStore
   * @category Data
   */
  /**
   * Get/set resources, applies to the backing project's ResourceStore.
   * @member {Scheduler.model.ResourceModel[]} resources
   * @accepts {Scheduler.model.ResourceModel[]|Scheduler.model.ResourceModelConfig[]}
   * @category Data
   */
  /**
   * Get/set the resource store instance of the backing project
   * @member {Scheduler.data.ResourceStore} resourceStore
   * @category Data
   */
  /**
   * Get/set assignments, applies to the backing project's AssignmentStore.
   * @member {Scheduler.model.AssignmentModel[]} assignments
   * @accepts {Scheduler.model.AssignmentModel[]|Object[]}
   * @category Data
   */
  /**
   * Get/set the event store instance of the backing project.
   * @member {Scheduler.data.AssignmentStore} assignmentStore
   * @category Data
   */
  /**
   * Get/set dependencies, applies to the backing projects DependencyStore.
   * @member {Scheduler.model.DependencyModel[]} dependencies
   * @accepts {Scheduler.model.DependencyModel[]|Scheduler.model.DependencyModelConfig[]}
   * @category Data
   */
  /**
   * Get/set the dependencies store instance of the backing project.
   * @member {Scheduler.data.DependencyStore} dependencyStore
   * @category Data
   */
  //endregion
  //region Events
  /**
   * Fired after rendering an event, when its element is available in DOM.
   * @event renderEvent
   * @param {Scheduler.view.Scheduler} source This Scheduler
   * @param {Scheduler.model.EventModel} eventRecord The event record
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource record
   * @param {Scheduler.model.AssignmentModel} assignmentRecord The assignment record
   * @param {Object} renderData An object containing details about the event rendering, see
   *   {@link Scheduler.view.mixin.SchedulerEventRendering#config-eventRenderer} for details
   * @param {Boolean} isRepaint `true` if this render is a repaint of the event, updating its existing element
   * @param {Boolean} isReusingElement `true` if this render lead to the event reusing a released events element
   * @param {HTMLElement} element The event bar element
   */
  /**
   * Fired after releasing an event, useful to cleanup of custom content added on `renderEvent` or in `eventRenderer`.
   * @event releaseEvent
   * @param {Scheduler.view.Scheduler} source This Scheduler
   * @param {Scheduler.model.EventModel} eventRecord The event record
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource record
   * @param {Scheduler.model.AssignmentModel} assignmentRecord The assignment record
   * @param {Object} renderData An object containing details about the event rendering
   * @param {HTMLElement} element The event bar element
   */
  /**
   * Fired when clicking a resource header cell
   * @event resourceHeaderClick
   * @param {Scheduler.view.Scheduler} source This Scheduler
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource record
   * @param {Event} event The event
   */
  /**
   * Fired when double clicking a resource header cell
   * @event resourceHeaderDblclick
   * @param {Scheduler.view.Scheduler} source This Scheduler
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource record
   * @param {Event} event The event
   */
  /**
   * Fired when activating context menu on a resource header cell
   * @event resourceHeaderContextmenu
   * @param {Scheduler.view.Scheduler} source This Scheduler
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource record
   * @param {Event} event The event
   */
  /**
   * Triggered when a keydown event is observed if there are selected events.
   * @event eventKeyDown
   * @param {Scheduler.view.Scheduler} source This Scheduler
   * @param {Scheduler.model.EventModel[]} eventRecords The selected event records
   * @param {Scheduler.model.AssignmentModel[]} assignmentRecords The selected assignment records
   * @param {KeyboardEvent} event Browser event
   */
  /**
   * Triggered when a keyup event is observed if there are selected events.
   * @event eventKeyUp
   * @param {Scheduler.view.Scheduler} source This Scheduler
   * @param {Scheduler.model.EventModel[]} eventRecords The selected event records
   * @param {Scheduler.model.AssignmentModel[]} assignmentRecords The selected assignment records
   * @param {KeyboardEvent} event Browser event
   */
  //endregion
  //region Functions injected by features
  // For documentation & typings purposes
  /**
   * Opens an editor UI to edit the passed event.
   *
   * *NOTE: Only available when the {@link Scheduler/feature/EventEdit EventEdit} feature is enabled.*
   *
   * @function editEvent
   * @param {Scheduler.model.EventModel} eventRecord Event to edit
   * @param {Scheduler.model.ResourceModel} [resourceRecord] The Resource record for the event.
   * This parameter is needed if the event is newly created for a resource and has not been assigned, or when using
   * multi assignment.
   * @param {HTMLElement} [element] Element to anchor editor to (defaults to events element)
   * @category Feature shortcuts
   */
  /**
   * Returns the dependency record for a DOM element
   *
   * *NOTE: Only available when the {@link Scheduler/feature/Dependencies Dependencies} feature is enabled.*
   *
   * @function resolveDependencyRecord
   * @param {HTMLElement} element The dependency line element
   * @returns {Scheduler.model.DependencyModel} The dependency record
   * @category Feature shortcuts
   */
  //endregion
  //region Init
  afterConstruct() {
    const me = this;
    super.afterConstruct();
    me.ion({ scroll: "onVerticalScroll", thisObj: me });
    if (me.createEventOnDblClick) {
      me.ion({ scheduledblclick: me.onTimeAxisCellDblClick });
    }
    me.ion({ splitterDragStart: "internalOnSplitterDragStart" });
  }
  //endregion
  //region Overrides
  onPaintOverride() {}
  //endregion
  //region Config getters/setters
  // Placeholder getter/setter for mixins, please make any changes needed to SchedulerStores#store instead
  get store() {
    return super.store;
  }
  set store(store) {
    super.store = store;
  }
  /**
   * Returns an object defining the range of visible resources
   * @property {Object}
   * @property {Scheduler.model.ResourceModel} visibleResources.first First visible resource
   * @property {Scheduler.model.ResourceModel} visibleResources.last Last visible resource
   * @readonly
   * @category Resources
   */
  get visibleResources() {
    var _a4, _b;
    const me = this;
    if (me.isVertical) {
      return me.currentOrientation.visibleResources;
    }
    return {
      first: me.store.getById(
        (_a4 = me.firstVisibleRow) == null ? void 0 : _a4.id,
      ),
      last: me.store.getById((_b = me.lastVisibleRow) == null ? void 0 : _b.id),
    };
  }
  //endregion
  //region Event handlers
  onLocaleChange() {
    this.currentOrientation.onLocaleChange();
    super.onLocaleChange();
  }
  onTimeAxisCellDblClick({ date: startDate, resourceRecord, row }) {
    this.createEvent(startDate, resourceRecord, row);
  }
  onVerticalScroll({ scrollTop }) {
    this.currentOrientation.updateFromVerticalScroll(scrollTop);
  }
  internalOnSplitterDragStart() {
    if (this.isHorizontal) {
      if (
        Object.keys(this.foregroundCanvas.syncIdMap).length >
        this.liveRedrawWhileMovingSplitterThreshold
      ) {
        this.suspendRefresh();
        this.ion({
          splitterDragEnd: () => this.resumeRefresh(true, false),
          once: true,
        });
      }
    }
  }
  /**
   * Called when new event is created.
   * Сan be overridden to supply default record values etc.
   * @param {Scheduler.model.EventModel} eventRecord Newly created event
   * @category Scheduled events
   */
  onEventCreated(eventRecord) {}
  //endregion
  //region Mode
  /**
   * Checks if scheduler is in horizontal mode
   * @returns {Boolean}
   * @readonly
   * @category Common
   * @private
   */
  get isHorizontal() {
    return this.mode === "horizontal";
  }
  /**
   * Checks if scheduler is in vertical mode
   * @returns {Boolean}
   * @readonly
   * @category Common
   * @private
   */
  get isVertical() {
    return this.mode === "vertical";
  }
  /**
   * Get mode (horizontal/vertical)
   * @property {'horizontal'|'vertical'}
   * @readonly
   * @category Common
   */
  get mode() {
    return this._mode;
  }
  set mode(mode) {
    const me = this;
    me._mode = mode;
    if (!me[mode]) {
      me.element.classList.add(`b-sch-${mode}`);
      if (mode === "horizontal") {
        me.horizontal = new HorizontalRendering(me);
        if (me.isPainted) {
          me.horizontal.init();
        }
      } else if (mode === "vertical") {
        me.vertical = new VerticalRendering(me);
        if (me.rendered) {
          me.vertical.init();
        }
      }
    }
  }
  get currentOrientation() {
    return this[this.mode];
  }
  //endregion
  //region Dom event dummies
  // this is ugly, but needed since super cannot be called from SchedulerDomEvents mixin...
  onElementKeyDown(event) {
    return super.onElementKeyDown(event);
  }
  onElementKeyUp(event) {
    return super.onElementKeyUp(event);
  }
  onElementMouseOver(event) {
    return super.onElementMouseOver(event);
  }
  onElementMouseOut(event) {
    return super.onElementMouseOut(event);
  }
  //endregion
  //region Feature hooks
  // Called for each event during drop
  processEventDrop() {}
  processCrossSchedulerEventDrop() {}
  // Called before event drag starts
  beforeEventDragStart() {}
  // Called after event drag starts
  afterEventDragStart() {}
  // Called after aborting a drag
  afterEventDragAbortFinalized() {}
  // Called during event drag validation
  checkEventDragValidity() {}
  // Called after event resizing starts
  afterEventResizeStart() {}
  // Called after generating a DomConfig for an event
  afterRenderEvent() {}
  //endregion
  //region Scheduler specific date mapping functions
  get hasEventEditor() {
    return Boolean(this.eventEditingFeature);
  }
  get eventEditingFeature() {
    const { eventEdit, taskEdit, simpleEventEdit } = this.features;
    return (eventEdit == null ? void 0 : eventEdit.enabled)
      ? eventEdit
      : (taskEdit == null ? void 0 : taskEdit.enabled)
        ? taskEdit
        : (simpleEventEdit == null ? void 0 : simpleEventEdit.enabled)
          ? simpleEventEdit
          : null;
  }
  /**
   * Creates an event on the specified date (and scrolls it into view), for the specified resource which conforms to
   * this scheduler's {@link #config-createEventOnDblClick} setting.
   *
   * NOTE: If the scheduler is readonly, or resource type is invalid (group header), or if `allowOverlap` is `false`
   * and slot is already occupied - no event is created.
   *
   * This method may be called programmatically by application code if the `createEventOnDblClick` setting
   * is `false`, in which case the default values for `createEventOnDblClick` will be used.
   *
   * If the {@link Scheduler.feature.EventEdit} feature is active, the new event
   * will be displayed in the event editor.
   * @param {Date} date The date to add the event at.
   * @param {Scheduler.model.ResourceModel} resourceRecord The resource to create the event for.
   * @category Scheduled events
   */
  async createEvent(startDate, resourceRecord) {
    var _a4, _b;
    const me = this,
      { enableEventAnimations, eventStore, assignmentStore, hasEventEditor } =
        me,
      resourceRecords = [resourceRecord],
      useEventModelDefaults = me.createEventOnDblClick.useEventModelDefaults,
      defaultDuration = useEventModelDefaults
        ? eventStore.modelClass.defaultValues.duration
        : 1,
      defaultDurationUnit = useEventModelDefaults
        ? eventStore.modelClass.defaultValues.durationUnit
        : me.timeAxis.unit,
      eventRecord = eventStore.createRecord({
        startDate,
        endDate: DateHelper.add(
          startDate,
          defaultDuration,
          defaultDurationUnit,
        ),
        duration: defaultDuration,
        durationUnit: defaultDurationUnit,
        name: me.L("L{Object.newEvent}"),
      });
    if (
      me.readOnly ||
      resourceRecord.isSpecialRow ||
      resourceRecord.readOnly ||
      (!me.allowOverlap &&
        !me.isDateRangeAvailable(
          eventRecord.startDate,
          eventRecord.endDate,
          null,
          resourceRecord,
        ))
    ) {
      return;
    }
    (_a4 = me.eventEditingFeature) == null ? void 0 : _a4.captureStm(true);
    eventRecord.isCreating = hasEventEditor;
    me.onEventCreated(eventRecord);
    const assignmentRecords =
      assignmentStore == null
        ? void 0
        : assignmentStore.assignEventToResource(eventRecord, resourceRecord);
    if (
      me.trigger("beforeEventAdd", {
        eventRecord,
        resourceRecords,
        assignmentRecords,
      }) === false
    ) {
      assignmentStore == null
        ? void 0
        : assignmentStore.remove(assignmentRecords);
      (_b = me.eventEditingFeature) == null ? void 0 : _b.freeStm(false);
      return;
    }
    me.enableEventAnimations = false;
    eventStore.add(eventRecord);
    me.project
      .commitAsync()
      .then(() => (me.enableEventAnimations = enableEventAnimations));
    me.isCreating = true;
    me.refreshRows();
    me.isCreating = false;
    await me.scrollEventIntoView(eventRecord);
    me.trigger("eventAutoCreated", {
      eventRecord,
      resourceRecord,
    });
    if (hasEventEditor) {
      me.editEvent(
        eventRecord,
        resourceRecord,
        me.getEventElement(eventRecord),
      );
    }
  }
  /**
   * Checks if a date range is allocated or not for a given resource.
   * @param {Date} start The start date
   * @param {Date} end The end date
   * @param {Scheduler.model.EventModel|null} excludeEvent An event to exclude from the check (or null)
   * @param {Scheduler.model.ResourceModel} resource The resource
   * @returns {Boolean} True if the timespan is available for the resource
   * @category Dates
   */
  isDateRangeAvailable(start, end, excludeEvent, resource) {
    return this.eventStore.isDateRangeAvailable(
      start,
      end,
      excludeEvent,
      resource,
    );
  }
  //endregion
  /**
   * Suspends UI refresh on store operations.
   *
   * Multiple calls to `suspendRefresh` stack up, and will require an equal number of `resumeRefresh` calls to
   * actually resume UI refresh.
   *
   * @function suspendRefresh
   * @category Rendering
   */
  /**
   * Resumes UI refresh on store operations.
   *
   * Multiple calls to `suspendRefresh` stack up, and will require an equal number of `resumeRefresh` calls to
   * actually resume UI refresh.
   *
   * Specify `true` as the first param to trigger a refresh if this call unblocked the refresh suspension.
   * If the underlying project is calculating changes, the refresh will be postponed until it is done.
   *
   * @param {Boolean} [trigger] `true` to trigger a refresh, if this resume unblocks suspension
   * @privateparam {Boolean} [useTransitions] `false` to block transitions
   * @category Rendering
   */
  async resumeRefresh(
    trigger = VersionHelper.checkVersion("core", "6.0", ">="),
    useTransitions = true,
  ) {
    super.resumeRefresh(false);
    const me = this;
    if (!me.refreshSuspended && trigger) {
      if (!me.isEngineReady) {
        me.currentOrientation.refreshAllWhenReady = true;
        return me.project.commitAsync();
      }
      if (!me.isDestroyed) {
        if (useTransitions) {
          me.refreshWithTransition();
        } else {
          me.refresh();
        }
      }
    }
  }
  //region Appearance
  // Overrides grid to take crudManager loading into account
  toggleEmptyText() {
    var _a4;
    const me = this;
    if (me.bodyContainer) {
      DomHelper.toggleClasses(
        me.bodyContainer,
        "b-grid-empty",
        !(
          me.resourceStore.count > 0 ||
          ((_a4 = me.crudManager) == null ? void 0 : _a4.isLoading)
        ),
      );
    }
  }
  // Overrides Grids base implementation to return a correctly calculated height for the row. Also stores it in
  // RowManagers height map, which is used to calculate total height etc.
  getRowHeight(resourceRecord) {
    if (this.isHorizontal) {
      const height = this.currentOrientation.calculateRowHeight(resourceRecord);
      this.rowManager.storeKnownHeight(resourceRecord.id, height);
      return height;
    }
  }
  // Calculates the height for specified rows. Call when changes potentially makes its height invalid
  calculateRowHeights(resourceRecords, silent = false) {
    const { store } = this;
    for (const resourceRecord of resourceRecords) {
      if (resourceRecord && store.isAvailable(resourceRecord)) {
        this.getRowHeight(resourceRecord);
      }
    }
    if (!silent) {
      this.rowManager.estimateTotalHeight(true);
    }
  }
  // Calculate heights for all rows (up to the preCalculateHeightLimit)
  calculateAllRowHeights(silent = false) {
    const { store, rowManager } = this,
      count = Math.min(store.count, this.preCalculateHeightLimit);
    if (count) {
      rowManager.clearKnownHeights();
      for (let i = 0; i < count; i++) {
        this.getRowHeight(store.getAt(i));
      }
      if (!silent) {
        rowManager.estimateTotalHeight(true);
      }
    }
  }
  //endregion
  //region Calendar Mode Interface
  // These are all internal and match up w/CalendarMixin
  /**
   * Returns the date or ranges of included dates as an array. If only the {@link #config-startDate} is significant,
   * the array will have that date as its only element. Otherwise, a range of dates is returned as a two-element
   * array with `[0]` is the {@link #config-startDate} and `[1]` is the {@link #property-lastDate}.
   * @member {Date[]}
   * @internal
   */
  get dateBounds() {
    const me = this,
      ret = [me.startDate];
    if (me.range === "week") {
      ret.push(me.lastDate);
    }
    return ret;
  }
  get defaultDescriptionFormat() {
    return descriptionFormats[this.range];
  }
  /**
   * The last day that is included in the date range. This is different than {@link #config-endDate} since that date
   * is not inclusive. For example, an `endDate` of 2022-07-21 00:00:00 indicates that the time range ends at that
   * time, and so 2022-07-21 is _not_ in the range. In this example, `lastDate` would be 2022-07-20 since that is the
   * last day included in the range.
   * @member {Date}
   * @internal
   */
  get lastDate() {
    const lastDate = this.endDate;
    return lastDate && DateHelper.add(lastDate, -1, "day");
  }
  getEventRecord(target) {
    target = DomHelper.getEventElement(target);
    return this.resolveEventRecord(target);
  }
  getResourceRecord(domEvent) {
    return this.resolveResourceRecord(domEvent);
  }
  getEventElement(eventRecord) {
    return this.getElementFromEventRecord(eventRecord);
  }
  changeRange(unit) {
    return DateHelper.normalizeUnit(unit);
  }
  updateRange(unit) {
    if (!this.isConfiguring) {
      const currentDate = this.date,
        newDate = (this.date = DateHelper.startOf(currentDate, unit));
      if (currentDate.getTime() === newDate.getTime()) {
        this.updateDate(newDate);
      }
    }
  }
  changeStepUnit(unit) {
    return DateHelper.normalizeUnit(unit);
  }
  updateDate(newDate) {
    const me = this,
      start = DateHelper.startOf(newDate, me.range);
    me.setTimeSpan(start, DateHelper.add(start, 1, me.range));
    me.visibleDate = {
      date: DateHelper.max(newDate, me.timeAxis.startDate),
      block: "start",
      animate: me.isPainted,
    };
    me.trigger("descriptionChange");
  }
  updateScrollBuffer(value) {
    if (!this.isConfiguring) {
      this.currentOrientation.scrollBuffer = value;
    }
  }
  previous() {
    this.date = DateHelper.add(this.date, -1, this.stepUnit);
  }
  next() {
    this.date = DateHelper.add(this.date, 1, this.stepUnit);
  }
  //endregion
  /**
   * Assigns and schedules an unassigned event record (+ adds it to this Scheduler's event store unless already in it).
   * @param {Object} config The config containing data about the event record to schedule
   * @param {Date} config.startDate The start date
   * @param {Scheduler.model.EventModel|EventModelConfig} config.eventRecord Event (or data for it) to assign and schedule
   * @param {Scheduler.model.EventModel} [config.parentEventRecord] Parent event to add the event to (to nest it),
   * only applies when using the NestedEvents feature
   * @param {Scheduler.model.ResourceModel} config.resourceRecord Resource to assign the event to
   * @param {HTMLElement} [config.element] The element if you are dragging an element from outside the scheduler
   * @category Scheduled events
   */
  async scheduleEvent({ startDate, eventRecord, resourceRecord, element }) {
    const me = this;
    if (!me.eventStore.includes(eventRecord)) {
      [eventRecord] = me.eventStore.add(eventRecord);
    }
    eventRecord.startDate = startDate;
    eventRecord.assign(resourceRecord);
    if (element) {
      const eventRect = Rectangle.from(element, me.foregroundCanvas);
      DomHelper.setTranslateXY(element, 0, 0);
      DomHelper.setTopLeft(element, eventRect.y, eventRect.x);
      DomSync.addChild(
        me.foregroundCanvas,
        element,
        eventRecord.assignments[0].id,
      );
    }
    await me.project.commitAsync();
  }
};
//region Config
__publicField(SchedulerBase, "$name", "SchedulerBase");
// Factoryable type name
__publicField(SchedulerBase, "type", "schedulerbase");
__publicField(SchedulerBase, "configurable", {
  /**
   * Get/set the scheduler's read-only state. When set to `true`, any UIs for modifying data are disabled.
   * @member {Boolean} readOnly
   * @category Misc
   */
  /**
   * Configure as `true` to make the scheduler read-only, by disabling any UIs for modifying data.
   *
   * __Note that checks MUST always also be applied at the server side.__
   * @config {Boolean} readOnly
   * @default false
   * @category Misc
   */
  /**
   * The date to display when used as a component of a Calendar.
   *
   * This is required by the Calendar Mode Interface.
   *
   * @config {Date}
   * @category Calendar integration
   */
  date: {
    value: null,
    $config: {
      equal: "date",
    },
  },
  /**
   * Unit used to control how large steps to take when clicking the previous and next buttons in the Calendar
   * UI. Only applies when used as a component of a Calendar.
   *
   * Suitable units depend on configured {@link #config-range}, a smaller or equal unit is recommended.
   *
   * @config {DurationUnit}
   * @default
   * @category Calendar integration
   */
  stepUnit: "week",
  /**
   * Unit used to set the length of the time axis when used as a component of a Calendar. Suitable units are
   * `'month'`, `'week'` and `'day'`.
   *
   * @config {'day'|'week'|'month'}
   * @category Calendar integration
   * @default
   */
  range: "week",
  /**
   * When the scheduler is used in a Calendar, this function provides the textual description for the
   * Calendar's toolbar.
   *
   * ```javascript
   *  descriptionRenderer : scheduler => {
   *      const
   *          count = scheduler.eventStore.records.filter(
   *              eventRec => DateHelper.intersectSpans(
   *                  scheduler.startDate, scheduler.endDate,
   *                  eventRec.startDate, eventRec.endDate)).length,
   *          startDate = DateHelper.format(scheduler.startDate, 'DD/MM/YYY'),
   *          endData = DateHelper.format(scheduler.endDate, 'DD/MM/YYY');
   *
   *      return `${startDate} - ${endData}, ${count} event${count === 1 ? '' : 's'}`;
   *  }
   * ```
   * @config {Function}
   * @param {Scheduler.view.SchedulerBase} view The active view.
   * @returns {String}
   * @category Calendar integration
   */
  /**
   * A method allowing you to define date boundaries that will constrain resize, create and drag drop
   * operations. The method will be called with the Resource record, and the Event record.
   *
   * ```javascript
   *  new Scheduler({
   *      getDateConstraints(resourceRecord, eventRecord) {
   *          // Assuming you have added these extra fields to your own EventModel subclass
   *          const { minStartDate, maxEndDate } = eventRecord;
   *
   *          return {
   *              start : minStartDate,
   *              end   : maxEndDate
   *          };
   *      }
   *  });
   * ```
   * @param {Scheduler.model.ResourceModel} [resourceRecord] The resource record
   * @param {Scheduler.model.EventModel} [eventRecord] The event record
   * @returns {Object} Constraining object containing `start` and `end` constraints. Omitting either
   * will mean that end is not constrained. So you can prevent a resize or move from moving *before*
   * a certain time while not constraining the end date.
   * @returns {Date} [return.start] Start date
   * @returns {Date} [return.end] End date
   * @config {Function}
   * @category Scheduled events
   */
  getDateConstraints: null,
  /**
   * The time axis column config for vertical {@link Scheduler.view.SchedulerBase#config-mode}.
   *
   * Object with {@link Scheduler.column.VerticalTimeAxisColumn} configuration.
   *
   * This object will be used to configure the vertical time axis column instance.
   *
   * The config allows configuring the `VerticalTimeAxisColumn` instance used in vertical mode with any Column options that apply to it.
   *
   * Example:
   *
   * ```javascript
   * new Scheduler({
   *     mode     : 'vertical',
   *     features : {
   *         filterBar : true
   *     },
   *     verticalTimeAxisColumn : {
   *         text  : 'Filter by event name',
   *         width : 180,
   *         filterable : {
   *             // add a filter field to the vertical column access header
   *             filterField : {
   *                 type        : 'text',
   *                 placeholder : 'Type to search',
   *                 onChange    : ({ value }) => {
   *                     // filter event by name converting to lowerCase to be equal comparison
   *                     scheduler.eventStore.filter({
   *                         filters : event => event.name.toLowerCase().includes(value.toLowerCase()),
   *                         replace : true
   *                     });
   *                 }
   *             }
   *         }
   *     },
   *     ...
   * });
   * ```
   *
   * @config {VerticalTimeAxisColumnConfig}
   * @category Time axis
   */
  verticalTimeAxisColumn: {},
  /**
   * See {@link Scheduler.view.Scheduler#keyboard-shortcuts Keyboard shortcuts} for details
   * @config {Object<String,String>} keyMap
   * @category Common
   */
  /**
   * If true, a new event will be created when user double-clicks on a time axis cell (if scheduler is not in
   * read only mode).
   *
   * The duration / durationUnit of the new event will be 1 time axis tick (default), or it can be read from
   * the {@link Scheduler.model.EventModel#field-duration} and
   * {@link Scheduler.model.EventModel#field-durationUnit} fields.
   *
   * Set to `false` to not create events on double click.
   * @config {Boolean|Object} createEventOnDblClick
   * @param {Boolean} [createEventOnDblClick.useEventModelDefaults] set to `true` to set default duration
   * based on the defaults specified by the {@link Scheduler.model.EventModel#field-duration} and
   * {@link Scheduler.model.EventModel#field-durationUnit} fields.
   * @default
   * @category Scheduled events
   */
  createEventOnDblClick: true,
  /**
   * Number of pixels to horizontally extend the visible render zone by, controlling the events that will be
   * rendered. You can use this to increase or reduce the amount of event rendering happening when scrolling
   * along a horizontal time axis. This can be useful if you render huge amount of events.
   *
   * To force the scheduler to render all events within the TimeAxis start & end dates, set this to -1.
   * The initial render will take slightly longer but no extra event rendering will take place when scrolling.
   *
   * NOTE: This is an experimental API which might change in future releases.
   * @config {Number}
   * @default
   * @internal
   * @category Experimental
   */
  scrollBuffer: 0,
  // A CSS class identifying areas where events can be scheduled using drag-create, double click etc.
  schedulableAreaSelector: ".b-sch-timeaxis-cell",
  scheduledEventName: "event",
  sortFeatureStore: "resourceStore",
  /**
   * If set to `true` this will show a color field in the {@link Scheduler.feature.EventEdit} editor and also a
   * picker in the {@link Scheduler.feature.EventMenu}. Both enables the user to choose a color which will be
   * applied to the event bar's background. See EventModel's
   * {@link Scheduler.model.mixin.EventModelMixin#field-eventColor} config.
   * config.
   * @config {Boolean}
   * @default false
   * @category Misc
   */
  showEventColorPickers: null,
  /**
   * By default, scrolling the schedule will update the {@link #property-timelineContext} to reflect the new
   * currently hovered context. When displaying a large number of events on screen at the same time, this will
   * have a slight impact on scrolling performance. In such scenarios, opt out of this behavior by setting
   * this config to `false`.
   * @default
   * @prp {Boolean}
   * @category Misc
   */
  updateTimelineContextOnScroll: true,
});
SchedulerBase.initClass();
SchedulerBase._$name = "SchedulerBase";

// ../Scheduler/lib/Scheduler/widget/EventColorPicker.js
var EventColorPicker = class extends ColorPicker {
  colorSelected({ color }) {
    if (this.record) {
      this.record.eventColor = color;
    }
  }
};
__publicField(EventColorPicker, "$name", "EventColorPicker");
__publicField(EventColorPicker, "type", "eventcolorpicker");
__publicField(EventColorPicker, "configurable", {
  colorClasses: SchedulerBase.eventColors,
  colorClassPrefix: "b-sch-",
  /**
   * @hideconfigs colors
   */
  colors: null,
  /**
   * Provide a {@link Scheduler.model.EventModel} instance to update it's
   * {@link Scheduler.model.mixin.EventModelMixin#field-eventColor} field
   * @config {Scheduler.model.EventModel}
   */
  record: null,
});
EventColorPicker.initClass();
EventColorPicker._$name = "EventColorPicker";

// ../Scheduler/lib/Scheduler/column/EventColorColumn.js
var EventColorColumn = class extends ColorColumn {};
__publicField(EventColorColumn, "$name", "EventColorColumn");
__publicField(EventColorColumn, "type", "eventcolor");
__publicField(EventColorColumn, "defaults", {
  colorEditorType: "eventcolorpicker",
  field: "eventColor",
});
ColumnStore.registerColumnType(EventColorColumn);
EventColorColumn._$name = "EventColorColumn";

// ../Scheduler/lib/Scheduler/column/ResourceCollapseColumn.js
var ResourceCollapseColumn = class extends Column {
  static get $name() {
    return "ResourceCollapseColumn";
  }
  static get type() {
    return "resourceCollapse";
  }
  static get defaults() {
    return {
      /** @hideconfigs renderer */
      width: "3em",
      align: "center",
      sortable: false,
      groupable: false,
      editor: false,
      minWidth: 0,
      cellCls: "b-resourcecollapse-cell",
      renderer: ({ record }) => ({
        tag: "i",
        class: {
          "b-icon": 1,
          "b-icon-expand-resource": 1,
          "b-flip": record.eventLayout !== "none",
        },
      }),
    };
  }
  onCellClick({ record, event }) {
    if (!record.isSpecialRow) {
      event.preventDefault();
      record.eventLayout = record.eventLayout !== "none" ? "none" : "stack";
    }
  }
};
ColumnStore.registerColumnType(ResourceCollapseColumn);
ResourceCollapseColumn._$name = "ResourceCollapseColumn";

// ../Scheduler/lib/Scheduler/column/ResourceInfoColumn.js
var ResourceInfoColumn = class extends Column {
  static get $name() {
    return "ResourceInfoColumn";
  }
  static get type() {
    return "resourceInfo";
  }
  static get fields() {
    return [
      "showEventCount",
      "showRole",
      "showMeta",
      "showImage",
      "validNames",
      "autoScaleThreshold",
      "useNameAsImageName",
    ];
  }
  static get defaults() {
    return {
      /** @hideconfigs renderer */
      /**
       * Show image. Looks for image name in fields on the resource in the following order: 'imageUrl', 'image',
       * 'name'. Set `showImage` to a field name to use a custom field. Set `Scheduler.resourceImagePath` to
       * specify where to load images from. If no extension found, defaults to
       * {@link Scheduler.view.mixin.SchedulerEventRendering#config-resourceImageExtension}.
       * @config {Boolean}
       * @default
       */
      showImage: true,
      /**
       * Show number of events assigned to the resource below the name.
       * @config {Boolean}
       * @default
       */
      showEventCount: true,
      /**
       * A template string to render any extra information about the resource below the name
       * @config {Function}
       * @param {Scheduler.model.ResourceModel} resourceRecord The record representing the current row
       * @returns {String|null}
       */
      showMeta: null,
      /**
       * Show resource role below the name. Specify `true` to display data from the `role` field, or specify a field
       * name to read this value from.
       * @config {Boolean|String}
       * @default
       */
      showRole: false,
      /**
       * Valid image names. Set to `null` to allow all names.
       * @deprecated This will be removed in 6.0
       * @config {String[]}
       */
      validNames: null,
      /**
       * Specify 0 to prevent the column from adapting its content according to the used row height, or specify a
       * threshold (row height) at which scaling should start.
       * @config {Number}
       * @default
       */
      autoScaleThreshold: 40,
      /**
       * Use the resource name as the image name when no `image` is specified on the resource.
       * @config {Boolean}
       * @default
       */
      useNameAsImageName: true,
      field: "name",
      htmlEncode: false,
      width: 140,
      cellCls: "b-resourceinfo-cell",
      editor: VersionHelper.isTestEnv ? false : "text",
    };
  }
  construct(...args) {
    super.construct(...args);
    this.avatarRendering = new AvatarRendering({
      element: this.grid.element,
    });
  }
  doDestroy() {
    super.doDestroy();
    this.avatarRendering.destroy();
  }
  getImageURL(imageName) {
    const resourceImagePath = this.grid.resourceImagePath || "",
      parts = resourceImagePath.split("//"),
      urlPart = parts.length > 1 ? parts[1] : resourceImagePath,
      joined = StringHelper.joinPaths([urlPart || "", imageName || ""]);
    return parts.length > 1 ? parts[0] + "//" + joined : joined;
  }
  template(resourceRecord, value) {
    const me = this,
      { showImage, showRole, showMeta, showEventCount, grid } = me,
      {
        timeAxis,
        resourceImageExtension = "",
        defaultResourceImageName,
      } = grid,
      roleField = typeof showRole === "string" ? showRole : "role",
      count =
        showEventCount &&
        resourceRecord.eventStore.getEvents({
          includeOccurrences: grid.enableRecurringEvents,
          resourceRecord,
          startDate: timeAxis.startDate,
          endDate: timeAxis.endDate,
        }).length;
    let imageUrl;
    if (showImage && resourceRecord.image !== false) {
      if (resourceRecord.imageUrl) {
        imageUrl = resourceRecord.imageUrl;
      } else {
        const imageName =
          typeof showImage === "string"
            ? showImage
            : resourceRecord.image ||
              (value &&
                me.useNameAsImageName &&
                value.toLowerCase() + resourceImageExtension) ||
              defaultResourceImageName ||
              "";
        imageUrl = imageName && me.getImageURL(imageName);
        if (imageUrl && !imageName.includes(".")) {
          if (!me.validNames || me.validNames.includes(imageName)) {
            imageUrl += resourceImageExtension;
          }
        }
      }
    }
    return {
      class: "b-resource-info",
      children: [
        showImage &&
          me.avatarRendering.getResourceAvatar({
            resourceRecord,
            initials: resourceRecord.initials,
            color: resourceRecord.eventColor,
            iconCls: resourceRecord.iconCls,
            imageUrl,
            defaultImageUrl:
              defaultResourceImageName &&
              this.getImageURL(defaultResourceImageName),
          }),
        showRole || showEventCount || showMeta
          ? {
              tag: "dl",
              children: [
                {
                  tag: "dt",
                  text: value,
                },
                showRole
                  ? {
                      tag: "dd",
                      class: "b-resource-role",
                      text: resourceRecord.getValue(roleField),
                    }
                  : null,
                showEventCount
                  ? {
                      tag: "dd",
                      class: "b-resource-events",
                      html: me.L("L{eventCountText}", count),
                    }
                  : null,
                showMeta
                  ? {
                      tag: "dd",
                      class: "b-resource-meta",
                      html: me.showMeta(resourceRecord),
                    }
                  : null,
              ],
            }
          : value,
        // This becomes a text node, no HTML encoding needed
      ],
    };
  }
  defaultRenderer({ grid, record, cellElement, value, isExport }) {
    let result;
    if (record.isSpecialRow) {
      result = "";
    } else if (isExport) {
      result = value;
    } else {
      if (this.autoScaleThreshold && grid.rowHeight < this.autoScaleThreshold) {
        cellElement.style.fontSize = grid.rowHeight / 40 + "em";
      } else {
        cellElement.style.fontSize = "";
      }
      result = this.template(record, value);
    }
    return result;
  }
};
ColumnStore.registerColumnType(ResourceInfoColumn);
ResourceInfoColumn._$name = "ResourceInfoColumn";

// ../Scheduler/lib/Scheduler/column/ScaleColumn.js
var ScaleColumn = class extends Column {
  static get fields() {
    return ["scalePoints"];
  }
  static get defaults() {
    return {
      text: "\xA0",
      width: 40,
      minWidth: 40,
      field: "scalePoints",
      cellCls: "b-scale-cell",
      editor: false,
      sortable: false,
      groupable: false,
      filterable: false,
      alwaysClearCell: false,
      scalePoints: null,
    };
  }
  //endregion
  //region Constructor/Destructor
  onDestroy() {
    this.scaleWidget.destroy();
  }
  //endregion
  //region Internal
  set width(width) {
    super.width = width;
    this.scaleWidget.width = width;
  }
  get width() {
    return super.width;
  }
  applyValue(useProp, key, value) {
    if (key === "scalePoints") {
      this.scaleWidget[key] = value;
    }
    return super.applyValue(...arguments);
  }
  buildScaleWidget() {
    const me = this;
    const scaleWidget = new Scale({
      owner: me.grid,
      appendTo: me.grid.floatRoot,
      cls: "b-hide-offscreen",
      align: "right",
      scalePoints: me.scalePoints,
      monitorResize: false,
    });
    Object.defineProperties(scaleWidget, {
      width: {
        get() {
          return me.width;
        },
        set(width) {
          this.element.style.width = `${width}px`;
          this._width = me.width;
        },
      },
      height: {
        get() {
          return this._height;
        },
        set(height) {
          this.element.style.height = `${height}px`;
          this._height = height;
        },
      },
    });
    scaleWidget.width = me.width;
    return scaleWidget;
  }
  get scaleWidget() {
    const me = this;
    if (!me._scaleWidget) {
      me._scaleWidget = me.buildScaleWidget();
    }
    return me._scaleWidget;
  }
  //endregion
  //region Render
  renderer({
    cellElement,
    value,
    scaleWidgetConfig,
    scaleWidget = this.scaleWidget,
  }) {
    ObjectHelper.assign(
      scaleWidget,
      {
        scalePoints: value || this.scalePoints,
        height: this.grid.rowHeight,
      },
      scaleWidgetConfig,
    );
    scaleWidget.refresh();
    const scaleCloneElement = scaleWidget.element.cloneNode(true);
    scaleCloneElement.removeAttribute("id");
    scaleCloneElement.classList.remove("b-hide-offscreen");
    cellElement.innerHTML = "";
    cellElement.appendChild(scaleCloneElement);
  }
  //endregion
};
//region Config
__publicField(ScaleColumn, "$name", "ScaleColumn");
__publicField(ScaleColumn, "type", "scale");
__publicField(ScaleColumn, "isScaleColumn", true);
ColumnStore.registerColumnType(ScaleColumn);
ScaleColumn._$name = "ScaleColumn";

// ../Scheduler/lib/Scheduler/data/util/recurrence/RecurrenceLegend.js
var RecurrenceLegend = class extends Localizable_default() {
  static get $name() {
    return "RecurrenceLegend";
  }
  static get allDaysValueAsArray() {
    return ["SU", "MO", "TU", "WE", "TH", "FR", "SA"];
  }
  static get allDaysValue() {
    return this.allDaysValueAsArray.join(",");
  }
  static get workingDaysValue() {
    return this.allDaysValueAsArray
      .filter((day2, index) => !DateHelper.nonWorkingDays[index])
      .join(",");
  }
  static get nonWorkingDaysValue() {
    return this.allDaysValueAsArray
      .filter((day2, index) => DateHelper.nonWorkingDays[index])
      .join(",");
  }
  /**
   * Returns the provided recurrence description. The recurrence might be assigned to a timespan model,
   * in this case the timespan start date should be provided in the second argument.
   * @param {Scheduler.model.RecurrenceModel} recurrenceRecurrence model.
   * @param {Date} [timeSpanStartDate] The recurring timespan start date. Can be omitted if the recurrence is assigned
   * to a timespan model (and the timespan has {@link Scheduler.model.TimeSpan#field-startDate} filled). Then start
   * date will be retrieved from the model.
   * @returns {String} The recurrence description.
   */
  static getLegend(recurrence, timeSpanStartDate) {
    const me = this,
      {
        timeSpan,
        interval,
        days: days2,
        monthDays,
        months,
        positions,
      } = recurrence,
      startDate = timeSpanStartDate || timeSpan.startDate,
      tplData = { interval };
    let fn2;
    switch (recurrence.frequency) {
      case "DAILY":
        return interval === 1
          ? me.L("L{Daily}")
          : me.L("L{Every {0} days}", tplData);
      case "WEEKLY":
        if (days2 && days2.length) {
          tplData.days = me.getDaysLegend(days2);
        } else if (startDate) {
          tplData.days = DateHelper.getDayName(startDate.getDay());
        }
        return me.L(
          interval === 1 ? "L{Weekly on {1}}" : "L{Every {0} weeks on {1}}",
          tplData,
        );
      case "MONTHLY":
        if (days2 && days2.length && positions && positions.length) {
          tplData.days = me.getDaysLegend(days2, positions);
        } else if (monthDays && monthDays.length) {
          monthDays.sort((a, b) => a - b);
          tplData.days = me.arrayToText(monthDays);
        } else if (startDate) {
          tplData.days = startDate.getDate();
        }
        return me.L(
          interval === 1 ? "L{Monthly on {1}}" : "L{Every {0} months on {1}}",
          tplData,
        );
      case "YEARLY":
        if (days2 && days2.length && positions && positions.length) {
          tplData.days = me.getDaysLegend(days2, positions);
        } else {
          tplData.days = startDate.getDate();
        }
        if (months && months.length) {
          months.sort((a, b) => a - b);
          if (months.length > 2) {
            fn2 = (month2) => DateHelper.getMonthShortName(month2 - 1);
          } else {
            fn2 = (month2) => DateHelper.getMonthName(month2 - 1);
          }
          tplData.months = me.arrayToText(months, fn2);
        } else {
          tplData.months = DateHelper.getMonthName(startDate.getMonth());
        }
        return me.L(
          interval === 1
            ? "L{Yearly on {1} of {2}}"
            : "L{Every {0} years on {1} of {2}}",
          tplData,
        );
    }
  }
  static getDaysLegend(days2, positions) {
    const me = this,
      tplData = { position: "" };
    let fn2;
    if (positions && positions.length) {
      tplData.position = me.arrayToText(positions, (position) =>
        me.L(`L{position${position}}`),
      );
    }
    if (days2.length) {
      days2.sort(
        (a, b) =>
          RecurrenceDayRuleEncoder.decodeDay(a)[0] -
          RecurrenceDayRuleEncoder.decodeDay(b)[0],
      );
      switch (days2.join(",")) {
        case me.allDaysValue:
          tplData.days = me.L("L{day}");
          break;
        case me.workingDaysValue:
          tplData.days = me.L("L{weekday}");
          break;
        case me.nonWorkingDaysValue:
          tplData.days = me.L("L{weekend day}");
          break;
        default:
          if (days2.length > 2) {
            fn2 = (day2) =>
              DateHelper.getDayShortName(
                RecurrenceDayRuleEncoder.decodeDay(day2)[0],
              );
          } else {
            fn2 = (day2) =>
              DateHelper.getDayName(
                RecurrenceDayRuleEncoder.decodeDay(day2)[0],
              );
          }
          tplData.days = me.arrayToText(days2, fn2);
      }
    }
    return me.L("L{daysFormat}", tplData);
  }
  // Converts array of items to a human readable list.
  // For example: [1,2,3,4]
  // to: "1, 2, 3 and 4"
  static arrayToText(array, fn2) {
    if (fn2) {
      array = array.map(fn2);
    }
    return array.join(", ").replace(/,(?=[^,]*$)/, this.L("L{ and }"));
  }
};
RecurrenceLegend._$name = "RecurrenceLegend";

// ../Scheduler/lib/Scheduler/tooltip/ClockTemplate.js
var ClockTemplate = class extends Base {
  static get defaultConfig() {
    return {
      minuteHeight: 8,
      minuteTop: 2,
      hourHeight: 8,
      hourTop: 2,
      handLeft: 10,
      div: document.createElement("div"),
      scheduler: null,
      // may be passed to the constructor if needed
      // `b-sch-clock-day` for calendar icon
      // `b-sch-clock-hour` for clock icon
      template(data) {
        return `<div class="b-sch-clockwrap b-sch-clock-${data.mode || this.mode} ${data.cls || ""}">
                    <div class="b-sch-clock">
                        <div class="b-sch-hour-indicator">${data.date ? DateHelper.format(data.date, "MMM") : ""}</div>
                        <div class="b-sch-minute-indicator">${data.date ? DateHelper.format(data.date, "D") : ""}</div>
                        <div class="b-sch-clock-dot"></div>
                    </div>
                    <span class="b-sch-clock-text">${StringHelper.encodeHtml(data.text || "")}</span>
                </div>`;
      },
    };
  }
  generateContent(data) {
    return (this.div.innerHTML = this.template(data));
  }
  updateDateIndicator(el, date) {
    const hourIndicatorEl =
        el == null ? void 0 : el.querySelector(".b-sch-hour-indicator"),
      minuteIndicatorEl =
        el == null ? void 0 : el.querySelector(".b-sch-minute-indicator");
    if (
      date &&
      hourIndicatorEl &&
      minuteIndicatorEl &&
      BrowserHelper.isBrowserEnv
    ) {
      if (this.mode === "hour") {
        hourIndicatorEl.style.transform = `rotate(${(date.getHours() % 12) * 30}deg)`;
        minuteIndicatorEl.style.transform = `rotate(${date.getMinutes() * 6}deg)`;
      } else {
        hourIndicatorEl.style.transform = "none";
        minuteIndicatorEl.style.transform = "none";
      }
    }
  }
  set mode(mode) {
    this._mode = mode;
  }
  // `day` mode for calendar icon
  // `hour` mode for clock icon
  get mode() {
    if (this._mode) {
      return this._mode;
    }
    const unitLessThanDay =
        DateHelper.compareUnits(
          this.scheduler.timeAxisViewModel.timeResolution.unit,
          "day",
        ) < 0,
      formatContainsHourInfo = DateHelper.formatContainsHourInfo(
        this.scheduler.displayDateFormat,
      );
    return unitLessThanDay && formatContainsHourInfo ? "hour" : "day";
  }
  set template(template) {
    this._template = template;
  }
  /**
   * Get the clock template, which accepts an object of format { date, text }
   * @property {Function}
   * @param {*} Format object
   * @returns {String}
   */
  get template() {
    return this._template;
  }
};
ClockTemplate._$name = "ClockTemplate";

// ../Scheduler/lib/Scheduler/feature/base/DragBase.js
var DragBase = class extends InstancePlugin {
  //region Config
  static get defaultConfig() {
    return {
      // documented on Schedulers EventDrag feature and Gantt's TaskDrag
      tooltipTemplate: (data) => `
                <div class="b-sch-tip-${data.valid ? "valid" : "invalid"}">
                    ${data.startClockHtml}
                    ${data.endClockHtml}
                    <div class="b-sch-tip-message">${data.message}</div>
                </div>
            `,
      /**
       * Specifies whether or not to show tooltip while dragging event
       * @prp {Boolean}
       * @default
       */
      showTooltip: true,
      /**
       * When enabled, the event being dragged always "snaps" to the exact start date that it will have after drop.
       * @config {Boolean}
       * @default
       */
      showExactDropPosition: false,
      /*
       * The store from which the dragged items are mapped to the UI.
       * In Scheduler's implementation of this base class, this will be
       * an EventStore, in Gantt's implementations, this will be a TaskStore.
       * Because both derive from this base, we must refer to it as this.store.
       * @private
       */
      store: null,
      /**
       * An object used to configure the internal {@link Core.helper.DragHelper} class
       * @config {DragHelperConfig}
       */
      dragHelperConfig: null,
      tooltipCls: "b-eventdrag-tooltip",
      /**
       * Whether to allow the SNET constraint generated by an event drag to be placed in non-
       * working time. When `true` and the event is dragged so that its `startDate` is in non-working
       * time, the SNET constraint date will be kept on the non-working date where the task is dropped.
       * When `false`, snaps the SNET date to working time in the same way as the `startDate`. The
       * `startDate` is not affected by this config.
       *
       * Applies only to Scheduler Pro and Gantt.
       *
       * @config {Boolean}
       * @default false
       */
      allowNonWorkingTimeSNET: null,
    };
  }
  static get configurable() {
    return {
      /**
       * Set to `false` to allow dragging tasks outside the client Scheduler.
       * Useful when you want to drag tasks between multiple Scheduler instances
       * @config {Boolean}
       * @default
       */
      constrainDragToTimeline: true,
      // documented on Schedulers EventDrag feature, not used for Gantt
      constrainDragToResource: true,
      constrainDragToTimeSlot: false,
      /**
       * Yields the {@link Core.widget.Tooltip} which tracks the event during a drag operation.
       * @member {Core.widget.Tooltip} tip
       */
      /**
       * A config object to allow customization of the {@link Core.widget.Tooltip} which tracks
       * the event during a drag operation.
       * @config {TooltipConfig}
       */
      tip: {
        $config: ["lazy", "nullify"],
        value: {
          align: {
            align: "b-t",
            allowTargetOut: true,
          },
          autoShow: true,
          updateContentOnMouseMove: true,
        },
      },
      /**
       * The `eventDrag`and `taskDrag` events are normally only triggered when the drag operation will lead to a
       * change in date or assignment. By setting this config to `false`, that logic is bypassed to trigger events
       * for each native mouse move event.
       * @prp {Boolean}
       */
      throttleDragEvent: true,
    };
  }
  // Plugin configuration. This plugin chains some of the functions in Grid.
  static get pluginConfig() {
    return {
      chain: ["onInternalPaint"],
    };
  }
  //endregion
  //region Init
  internalSnapToPosition(snapTo) {
    var _a4;
    const { dragData } = this;
    (_a4 = this.snapToPosition) == null
      ? void 0
      : _a4.call(this, {
          assignmentRecord: dragData.assignmentRecord,
          eventRecord: dragData.eventRecord,
          resourceRecord: dragData.newResource || dragData.resourceRecord,
          startDate: dragData.startDate,
          endDate: dragData.endDate,
          snapTo,
        });
  }
  buildDragHelperConfig() {
    const me = this,
      {
        client,
        constrainDragToTimeline,
        constrainDragToResource,
        constrainDragToTimeSlot,
        dragHelperConfig = {},
      } = me,
      { timeAxisViewModel, isHorizontal } = client,
      lockY = isHorizontal ? constrainDragToResource : constrainDragToTimeSlot,
      lockX = isHorizontal ? constrainDragToTimeSlot : constrainDragToResource;
    if (me.externalDropTargetSelector) {
      dragHelperConfig.dropTargetSelector = `.b-timeaxissubgrid,${me.externalDropTargetSelector}`;
    }
    return Objects.merge(
      {
        name: me.constructor.name,
        // useful when debugging with multiple draggers
        positioning: "absolute",
        lockX,
        lockY,
        minX: true,
        // Allows dropping with start before time axis
        maxX: true,
        // Allows dropping with end after time axis
        constrain: false,
        cloneTarget: !constrainDragToTimeline,
        // If we clone event dragged bars, we assume ownership upon drop so we can reuse the element and have animations
        removeProxyAfterDrop: false,
        dragWithin: constrainDragToTimeline ? null : client.floatRoot,
        hideOriginalElement: true,
        dropTargetSelector: ".b-timelinebase",
        allowDropOutside: !constrainDragToTimeline,
        // A CSS class added to drop target while dragging events
        dropTargetCls: me.externalDropTargetSelector ? "b-drop-target" : "",
        outerElement: client.timeAxisSubGridElement,
        targetSelector: client.eventSelector,
        scrollManager: constrainDragToTimeline ? client.scrollManager : null,
        createProxy: (el) => me.createProxy(el),
        snapCoordinates: ({ element, newX, newY }) => {
          const { dragData } = me,
            timeline = this.currentOverClient;
          if (
            me.constrainDragToTimeline &&
            !me.constrainDragToTimeSlot &&
            (me.showExactDropPosition || timeAxisViewModel.snap)
          ) {
            const draggedEventRecord =
                dragData.draggedEntities[0].event ||
                dragData.draggedEntities[0],
              coordinate = me.getCoordinate(draggedEventRecord, element, [
                newX,
                newY,
              ]),
              snappedDate =
                timeline.fillTicks && client.timeAxis.isContinuous
                  ? dragData.startDate
                  : timeAxisViewModel.getDateFromPosition(coordinate, "round"),
              { calendar } = draggedEventRecord;
            if (
              !calendar ||
              (snappedDate &&
                calendar.isWorkingTime(
                  snappedDate,
                  DateHelper.add(snappedDate, draggedEventRecord.fullDuration),
                ))
            ) {
              const snappedPosition =
                snappedDate &&
                timeAxisViewModel.getPositionFromDate(snappedDate);
              if (
                snappedDate &&
                snappedDate >= client.startDate &&
                snappedPosition != null
              ) {
                if (isHorizontal) {
                  newX = snappedPosition;
                } else {
                  newY = snappedPosition;
                }
              }
            }
          }
          const snapTo = { x: newX, y: newY };
          me.internalSnapToPosition(snapTo);
          return snapTo;
        },
        internalListeners: {
          beforedragstart: "onBeforeDragStart",
          dragstart: "onDragStart",
          afterdragstart: "onAfterDragStart",
          drag: "onDrag",
          drop: "onDrop",
          abort: "onDragAbort",
          abortFinalized: "onDragAbortFinalized",
          reset: "onDragReset",
          thisObj: me,
        },
      },
      dragHelperConfig,
      {
        isElementDraggable: (el, event) => {
          return (
            (!dragHelperConfig ||
              !dragHelperConfig.isElementDraggable ||
              dragHelperConfig.isElementDraggable(el, event)) &&
            me.isElementDraggable(el, event)
          );
        },
      },
    );
  }
  /**
   * Called when scheduler is rendered. Sets up drag and drop and hover tooltip.
   * @private
   */
  onInternalPaint({ firstPaint }) {
    var _a4;
    const me = this,
      { client } = me;
    (_a4 = me.drag) == null ? void 0 : _a4.destroy();
    me.drag = DragHelper.new(me.buildDragHelperConfig());
    if (firstPaint) {
      client.rowManager.ion({
        changeTotalHeight: () => {
          var _a5;
          return me.updateYConstraint(
            (_a5 = me.dragData) == null
              ? void 0
              : _a5[`${client.scheduledEventName}Record`],
          );
        },
        thisObj: me,
      });
    }
    if (me.showTooltip) {
      me.clockTemplate = new ClockTemplate({
        scheduler: client,
      });
    }
  }
  doDestroy() {
    var _a4, _b, _c;
    (_a4 = this.drag) == null ? void 0 : _a4.destroy();
    (_b = this.clockTemplate) == null ? void 0 : _b.destroy();
    (_c = this.tip) == null ? void 0 : _c.destroy();
    super.doDestroy();
  }
  get tipId() {
    return `${this.client.id}-event-drag-tip`;
  }
  changeTip(tip, oldTip) {
    const me = this;
    if (tip) {
      const result = Tooltip.reconfigure(
        oldTip,
        Tooltip.mergeConfigs(
          {
            forElement: me.element,
            id: me.tipId,
            getHtml: me.getTipHtml.bind(me),
            cls: me.tooltipCls,
            owner: me.client,
          },
          tip,
        ),
        {
          owner: me.client,
          defaults: {
            type: "tooltip",
          },
        },
      );
      result.ion({ innerHtmlUpdate: "updateDateIndicator", thisObj: me });
      return result;
    } else {
      oldTip == null ? void 0 : oldTip.destroy();
    }
  }
  //endregion
  //region Drag events
  createProxy(element) {
    const proxy = element.cloneNode(true);
    delete proxy.id;
    proxy.classList.add(`b-sch-${this.client.mode}`);
    return proxy;
  }
  onBeforeDragStart({ context, event }) {
    var _a4;
    const me = this,
      { client } = me,
      dragData = me.getMinimalDragData(context, event),
      eventRecord =
        dragData == null
          ? void 0
          : dragData[`${client.scheduledEventName}Record`],
      resourceRecord = dragData.resourceRecord;
    if (
      client.readOnly ||
      me.disabled ||
      !eventRecord ||
      eventRecord.isDraggable === false ||
      eventRecord.readOnly ||
      (resourceRecord == null ? void 0 : resourceRecord.readOnly)
    ) {
      return false;
    }
    context.pointerStartDate = client.getDateFromXY(
      [context.startClientX, context.startPageY],
      null,
      false,
    );
    const result =
      me.triggerBeforeEventDrag(`before${client.capitalizedEventName}Drag`, {
        ...dragData,
        event,
        // to be deprecated
        context: {
          ...context,
          ...dragData,
        },
      }) !== false;
    if (result) {
      me.updateYConstraint(eventRecord, resourceRecord);
      (_a4 = client[`before${client.capitalizedEventName}DragStart`]) == null
        ? void 0
        : _a4.call(client, context, dragData);
    }
    return result;
  }
  onAfterDragStart({ context, event }) {}
  /**
   * Returns true if a drag operation is active
   * @property {Boolean}
   * @readonly
   */
  get isDragging() {
    var _a4;
    return (_a4 = this.drag) == null ? void 0 : _a4.isDragging;
  }
  // Checked by dependencies to determine if live redrawing is needed
  get isActivelyDragging() {
    return this.isDragging && !this.finalizing;
  }
  /**
   * Triggered when dragging of an event starts. Initializes drag data associated with the event being dragged.
   * @private
   */
  onDragStart({ context, event }) {
    var _a4, _b, _c;
    const me = this,
      client =
        (_a4 = me.findClientFromTarget(event, context)) != null
          ? _a4
          : me.client;
    me.currentOverClient = client;
    me.drag.unifiedProxy = me.unifiedDrag;
    me.onMouseOverNewTimeline(client, true);
    const dragData = (me.dragData = me.getDragData(context));
    me.suspendElementRedrawing(context.element);
    if (me.showTooltip && me.tip) {
      const tipTarget = dragData.context.dragProxy
        ? dragData.context.dragProxy.firstChild
        : context.element;
      me.tip.showBy(tipTarget);
    }
    me.triggerDragStart(dragData);
    (_b = client[`after${client.capitalizedEventName}DragStart`]) == null
      ? void 0
      : _b.call(client, context, dragData);
    const { eventMenu, taskMenu } = client.features,
      menuFeature = eventMenu || taskMenu;
    (_c = menuFeature == null ? void 0 : menuFeature.hideContextMenu) == null
      ? void 0
      : _c.call(menuFeature, false);
  }
  updateDateIndicator() {
    const { startDate, endDate } = this.dragData,
      { tip, clockTemplate } = this,
      endDateElement = tip.element.querySelector(".b-sch-tooltip-enddate");
    clockTemplate.updateDateIndicator(tip.element, startDate);
    endDateElement &&
      clockTemplate.updateDateIndicator(endDateElement, endDate);
  }
  findClientFromTarget(event, context) {
    let { target } = event;
    if (/^touch/.test(event.type)) {
      const center = Rectangle.from(context.element, null, true).center;
      target = DomHelper.elementFromPoint(center.x, center.y);
    }
    const client = Widget.fromElement(target, "timelinebase");
    return (client == null ? void 0 : client.isResourceHistogram)
      ? null
      : client;
  }
  /**
   * Triggered while dragging an event. Updates drag data, validation etc.
   * @private
   */
  onDrag({ context, event }) {
    const me = this,
      dd = me.dragData,
      start = dd.startDate;
    let client;
    if (me.constrainDragToTimeline) {
      client = me.client;
    } else {
      client = me.findClientFromTarget(event, dd.context);
    }
    me.updateDragContext(context, event);
    if (!client) {
      return;
    }
    if (client !== me.currentOverClient) {
      me.onMouseOverNewTimeline(client);
    }
    if (dd.dirty || !me.throttleDragEvent) {
      const valid = dd.valid;
      me.triggerEventDrag(dd, start);
      if (valid !== dd.valid) {
        dd.context.valid = dd.externalDragValidity = dd.valid;
      }
    }
    if (me.showTooltip && me.tip) {
      me.tip.lastAlignSpec.allowTargetOut = !dd.valid;
      me.tip.realign();
    }
  }
  onMouseOverNewTimeline(newTimeline, initial) {
    const me = this,
      {
        drag: { lockX, lockY },
      } = me,
      scrollables = [];
    me.currentOverClient.element.classList.remove(
      "b-dragging-" + me.currentOverClient.scheduledEventName,
    );
    newTimeline.element.classList.add(
      "b-dragging-" + newTimeline.scheduledEventName,
    );
    if (!initial) {
      me.currentOverClient.scrollManager.stopMonitoring();
    }
    if (!lockX) {
      scrollables.push({
        element: newTimeline.timeAxisSubGrid.scrollable.element,
        direction: "horizontal",
      });
    }
    if (!lockY) {
      scrollables.push({
        element: newTimeline.scrollable.element,
        direction: "vertical",
      });
    }
    newTimeline.scrollManager.startMonitoring({
      scrollables,
      callback: me.drag.onScrollManagerScrollCallback,
    });
    me.currentOverClient = newTimeline;
  }
  triggerBeforeEventDropFinalize(eventType, eventData, client) {
    client.trigger(eventType, eventData);
  }
  /**
   * Triggered when dropping an event. Finalizes the operation.
   * @private
   */
  onDrop({ context, event }) {
    var _a4;
    const me = this,
      { currentOverClient, dragData } = me;
    let modified = false;
    currentOverClient == null
      ? void 0
      : currentOverClient.scrollManager.stopMonitoring();
    (_a4 = me.tip) == null ? void 0 : _a4.hide();
    context.valid = context.valid && me.isValidDrop(dragData);
    // PATCHED by FI: Validate working hours on event drop
    if (context.valid && typeof window.__FI_VALIDATE_WORKING_TIME__ === 'function') {
      const targetResourceId = dragData.newResource?.id || dragData.resourceRecord?.id;
      const targetDate = dragData.startDate;
      if (targetResourceId && targetDate) {
        context.valid = context.valid && window.__FI_VALIDATE_WORKING_TIME__(targetResourceId, targetDate);
      }
    }
    me.drag.removeProxyAfterDrop = Boolean(dragData.externalDropTarget);
    if (context.valid && dragData.startDate && dragData.endDate) {
      let beforeDropTriggered = false;
      dragData.finalize = async (valid) => {
        if (beforeDropTriggered || dragData.async) {
          await me.finalize(valid);
        } else {
          context.valid = context.valid && valid;
        }
      };
      me.triggerBeforeEventDropFinalize(
        `before${currentOverClient.capitalizedEventName}DropFinalize`,
        {
          context: dragData,
          domEvent: event,
        },
        currentOverClient,
      );
      beforeDropTriggered = true;
      context.async = dragData.async;
      if (!context.async && !dragData.externalDropTarget) {
        modified =
          dragData.startDate - dragData.origStart !== 0 ||
          dragData.newResource !== dragData.resourceRecord;
      }
    }
    if (!context.async) {
      me.finalize(dragData.valid && context.valid && modified);
    }
  }
  onDragAbort({ context }) {
    var _a4, _b;
    const me = this;
    me.isAborting = true;
    (_a4 = me.currentOverClient) == null
      ? void 0
      : _a4.scrollManager.stopMonitoring();
    me.client.currentOrientation.onDragAbort({
      context,
      dragData: me.dragData,
    });
    me.resetDraggedElements();
    (_b = me.tip) == null ? void 0 : _b.hide();
    me.triggerDragAbort(me.dragData);
  }
  // Fired after any abort animation has completed (the point where we want to trigger redraw of progress lines etc)
  onDragAbortFinalized({ context }) {
    var _a4, _b;
    const me = this;
    me.triggerDragAbortFinalized(me.dragData);
    (_b = (_a4 = me.client)[
      `after${me.client.capitalizedEventName}DragAbortFinalized`
    ]) == null
      ? void 0
      : _b.call(_a4, context, me.dragData);
    me.isAborting = false;
  }
  // For the drag across multiple schedulers, tell all involved scroll managers to stop monitoring
  onDragReset({ source: dragHelper }) {
    var _a4;
    const me = this,
      currentTimeline = me.currentOverClient;
    if ((_a4 = dragHelper.context) == null ? void 0 : _a4.started) {
      me.resetDraggedElements();
      currentTimeline.trigger(`${currentTimeline.scheduledEventName}DragReset`);
    }
    currentTimeline == null
      ? void 0
      : currentTimeline.element.classList.remove(
          `b-dragging-${currentTimeline.scheduledEventName}`,
        );
    me.dragData = null;
  }
  resetDraggedElements() {
    const { dragData } = this,
      { eventBarEls, draggedEntities } = dragData;
    this.resumeRecordElementRedrawing(dragData.record);
    draggedEntities.forEach((record, i) => {
      this.resumeRecordElementRedrawing(record);
      eventBarEls[i].classList.remove(this.drag.draggingCls);
      eventBarEls[i].retainElement = false;
    });
    dragData.context.element.retainElement = false;
  }
  /**
   * Triggered internally on invalid drop.
   * @private
   */
  onInternalInvalidDrop(abort) {
    var _a4;
    const me = this,
      { context } = me.drag;
    (_a4 = me.tip) == null ? void 0 : _a4.hide();
    me.triggerAfterDrop(me.dragData, false);
    context.valid = false;
    if (abort) {
      me.drag.abort();
    }
  }
  //endregion
  //region Finalization & validation
  /**
   * Called on drop to update the record of the event being dropped.
   * @private
   * @param {Boolean} updateRecords Specify true to update the record, false to treat as invalid
   */
  async finalize(updateRecords) {
    const me = this,
      { dragData, currentOverClient } = me,
      clientEventTipFeature =
        currentOverClient.features.taskTooltip ||
        currentOverClient.features.eventTooltip;
    if (!dragData || me.finalizing) {
      return;
    }
    const { context, draggedEntities, externalDropTarget } = dragData;
    let result;
    me.finalizing = true;
    draggedEntities.forEach((record, i) => {
      me.resumeRecordElementRedrawing(record);
      dragData.eventBarEls[i].classList.remove(me.drag.draggingCls);
      dragData.eventBarEls[i].retainElement = false;
    });
    context.element.retainElement = false;
    if ((externalDropTarget && dragData.valid) || updateRecords) {
      result = me.updateRecords(dragData);
      if (!externalDropTarget && Objects.isPromise(result)) {
        context.async = true;
        await result;
      }
      if (!dragData.valid) {
        me.onInternalInvalidDrop(true);
      } else {
        if (context.async) {
          context.finalize();
        }
        if (externalDropTarget) {
          me.client.refreshRows(false);
        }
        me.triggerAfterDrop(dragData, true);
      }
    } else {
      me.onInternalInvalidDrop(context.async || dragData.async);
    }
    me.finalizing = false;
    if (
      clientEventTipFeature == null ? void 0 : clientEventTipFeature.enabled
    ) {
      clientEventTipFeature.disabled = true;
      currentOverClient.setTimeout(() => {
        clientEventTipFeature.disabled = false;
      }, 200);
    }
    return result;
  }
  //endregion
  //region Drag data
  getEventNewStartEndDates(eventRecord, timeDiff) {
    let startDate = this.adjustStartDate(eventRecord.startDate, timeDiff);
    let endDate;
    if (eventRecord.graph && !this.allowNonWorkingTimeSNET) {
      try {
        startDate = eventRecord.run("skipNonWorkingTime", startDate);
        endDate = eventRecord.run(
          "calculateProjectedXDateWithDuration",
          startDate,
          true,
          eventRecord.duration,
        );
      } catch (e) {
        return { valid: false };
      }
    } else {
      endDate = DateHelper.add(startDate, eventRecord.fullDuration);
    }
    return { startDate, endDate };
  }
  /**
   * Updates drag data's dates and validity (calls #validatorFn if specified)
   * @private
   */
  updateDragContext(info, event) {
    var _a4, _b, _c;
    const me = this,
      { drag } = me,
      dd = me.dragData,
      client = me.currentOverClient,
      { isHorizontal } = client,
      [record] = dd.draggedEntities,
      eventRecord = record.isAssignment ? record.event : record,
      lastDragStartDate = dd.startDate,
      constrainToTimeSlot =
        me.constrainDragToTimeSlot || (isHorizontal ? drag.lockX : drag.lockY);
    dd.browserEvent = event;
    Object.assign(dd, me.getProductDragContext(dd));
    if (constrainToTimeSlot) {
      dd.timeDiff = 0;
    } else {
      let timeDiff;
      if (
        client.timeAxis.isContinuous ||
        (dd.startsOutsideView && dd.endsOutsideView)
      ) {
        const timeAxisPosition = client.isHorizontal
            ? (_a4 = info.pageX) != null
              ? _a4
              : info.startPageX
            : (_b = info.pageY) != null
              ? _b
              : info.startPageY,
          pointerDate = client.getDateFromCoordinate(
            timeAxisPosition,
            null,
            false,
            true,
          );
        timeDiff = dd.timeDiff = pointerDate - info.pointerStartDate;
        if (timeDiff !== null) {
          Object.assign(dd, me.getEventNewStartEndDates(eventRecord, timeDiff));
          if (dd.valid) {
            dd.timeDiff = dd.startDate - dd.origStart;
          }
        }
      } else {
        const range = me.resolveStartEndDates(info.element);
        dd.valid = Boolean(range.startDate && range.endDate);
        if (dd.valid) {
          timeDiff = range.startDate - dd.origStart;
        }
        if (timeDiff !== void 0) {
          if (eventRecord.graph && !this.allowNonWorkingTimeSNET) {
            dd.startDate = eventRecord.run(
              "skipNonWorkingTime",
              range.startDate,
            );
            dd.endDate = eventRecord.run(
              "calculateProjectedXDateWithDuration",
              range.startDate,
              true,
              eventRecord.duration,
            );
          } else {
            dd.startDate = range.startDate;
            dd.endDatee = range.endDate;
          }
        }
        dd.timeDiff = timeDiff;
      }
    }
    const positionDirty = (dd.dirty =
      dd.dirty || lastDragStartDate - dd.startDate !== 0);
    if (dd.valid) {
      if (
        me.constrainDragToTimeline &&
        (dd.endDate <= client.timeAxis.startDate ||
          dd.startDate >= client.timeAxis.endDate)
      ) {
        dd.valid = false;
        dd.context.message = me.L("L{EventDrag.noDropOutsideTimeline}");
      } else if (positionDirty || dd.externalDropTarget) {
        const result = (dd.externalDragValidity =
          !event || (info.pageX && me.checkDragValidity(dd, event)));
        if (!result || typeof result === "boolean") {
          dd.valid = result !== false;
          dd.context.message = "";
        } else {
          dd.valid = result.valid !== false;
          dd.context.message = result.message;
        }
      } else {
        dd.valid =
          dd.externalDragValidity !== false &&
          ((_c = dd.externalDragValidity) == null ? void 0 : _c.valid) !==
            false;
      }
    } else {
      dd.valid = false;
    }
    dd.context.valid = dd.valid;
  }
  suspendRecordElementRedrawing(record, suspend = true) {
    this.suspendElementRedrawing(this.getRecordElement(record), suspend);
    record.instanceMeta(this.client).retainElement = suspend;
  }
  resumeRecordElementRedrawing(record) {
    this.suspendRecordElementRedrawing(record, false);
  }
  suspendElementRedrawing(element, suspend = true) {
    if (element) {
      element.retainElement = suspend;
    }
  }
  resumeElementRedrawing(element) {
    this.suspendElementRedrawing(element, false);
  }
  /**
   * Initializes drag data (dates, constraints, dragged events etc). Called when drag starts.
   * @private
   * @param info
   * @returns {*}
   */
  getDragData(info) {
    const me = this,
      { client, drag } = me,
      productDragData = me.setupProductDragData(info),
      { record, eventBarEls, draggedEntities } = productDragData,
      { startEvent } = drag,
      timespan = record.isAssignment ? record.event : record,
      origStart = timespan.startDate,
      origEnd = timespan.endDate,
      timeAxis = client.timeAxis,
      startsOutsideView = origStart < timeAxis.startDate,
      endsOutsideView = origEnd > timeAxis.endDate,
      multiSelect = client.isSchedulerBase
        ? client.multiEventSelect
        : client.selectionMode.multiSelect,
      coordinate = me.getCoordinate(timespan, info.element, [
        info.elementStartX,
        info.elementStartY,
      ]),
      clientCoordinate = me.getCoordinate(timespan, info.element, [
        info.startClientX,
        info.startClientY,
      ]);
    me.suspendRecordElementRedrawing(record);
    draggedEntities.forEach((record2) =>
      me.suspendRecordElementRedrawing(record2),
    );
    if (record.isAssignment) {
      client.selectAssignment(record, startEvent.ctrlKey && multiSelect);
    } else {
      client.selectEvent(record, startEvent.ctrlKey && multiSelect);
    }
    const dragData = {
      context: info,
      ...productDragData,
      sourceDate: startsOutsideView
        ? origStart
        : client.getDateFromCoordinate(coordinate),
      screenSourceDate: client.getDateFromCoordinate(
        clientCoordinate,
        null,
        false,
      ),
      startDate: origStart,
      endDate: origEnd,
      timeDiff: 0,
      origStart,
      origEnd,
      startsOutsideView,
      endsOutsideView,
      duration: origEnd - origStart,
      browserEvent: startEvent,
      // So we can know if SHIFT/CTRL was pressed
    };
    eventBarEls.forEach((el) =>
      el.classList.remove("b-sch-event-hover", "b-active"),
    );
    if (eventBarEls.length > 1) {
      info.relatedElements = eventBarEls.slice(1);
    }
    return dragData;
  }
  //endregion
  //region Constraints
  // private
  setupConstraints(constrainRegion, elRegion, tickSize, constrained) {
    const me = this,
      xTickSize = !me.showExactDropPosition && tickSize > 1 ? tickSize : 0,
      yTickSize = 0;
    if (constrained) {
      me.setXConstraint(
        constrainRegion.left,
        constrainRegion.right - elRegion.width,
        xTickSize,
      );
    } else {
      me.setXConstraint(true, true, xTickSize);
    }
    me.setYConstraint(
      constrainRegion.top,
      constrainRegion.bottom - elRegion.height,
      yTickSize,
    );
  }
  updateYConstraint(eventRecord, resourceRecord) {
    const me = this,
      { client } = me,
      { context } = me.drag,
      tickSize = client.timeAxisViewModel.snapPixelAmount;
    if (context && !me.drag.lockY) {
      let constrainRegion;
      if (me.constrainDragToTimeline) {
        constrainRegion = client.getScheduleRegion(resourceRecord, eventRecord);
      } else {
        me.setYConstraint(null, null, tickSize);
        return;
      }
      me.setYConstraint(
        constrainRegion.top,
        constrainRegion.bottom - context.element.offsetHeight,
        tickSize,
      );
    } else {
      me.setYConstraint(null, null, tickSize);
    }
  }
  setXConstraint(iLeft, iRight, iTickSize) {
    const { drag } = this;
    drag.minX = iLeft;
    drag.maxX = iRight;
  }
  setYConstraint(iUp, iDown, iTickSize) {
    const { drag } = this;
    drag.minY = iUp;
    drag.maxY = iDown;
  }
  //endregion
  //region Other stuff
  adjustStartDate(startDate, timeDiff) {
    const rounded = this.client.timeAxis.roundDate(
      new Date(startDate - 0 + timeDiff),
      this.client.snapRelativeToEventStartDate ? startDate : false,
    );
    return this.constrainStartDate(rounded);
  }
  resolveStartEndDates(draggedElement) {
    const timeline = this.currentOverClient,
      { timeAxis } = timeline,
      proxyRect = Rectangle.from(
        draggedElement.querySelector(timeline.eventInnerSelector),
        timeline.timeAxisSubGridElement,
      ),
      dd = this.dragData,
      [record] = dd.draggedEntities,
      eventRecord = record.isAssignment ? record.event : record,
      fillSnap = timeline.fillTicks && timeline.snapRelativeToEventStartDate,
      totalDurationMS = eventRecord.endDate - eventRecord.startDate;
    let { start: startDate, end: endDate } =
      timeline.getStartEndDatesFromRectangle(
        proxyRect,
        fillSnap ? null : "round",
        totalDurationMS,
        true,
      );
    if (startDate && endDate) {
      if (fillSnap) {
        const offsetMS =
            eventRecord.startDate -
            DateHelper.startOf(eventRecord.startDate, timeAxis.unit),
          proxyMS = endDate - startDate,
          offsetPx = (offsetMS / proxyMS) * proxyRect.width;
        proxyRect.deflate(offsetPx, 0, 0, offsetPx);
        const proxyStart = proxyRect.getStart(
          timeline.rtl,
          !timeline.isVertical,
        );
        startDate = timeline.getDateFromCoordinate(proxyStart, null, true);
        startDate = timeAxis.roundDate(startDate, eventRecord.startDate);
      }
      startDate = this.adjustStartDate(startDate, 0);
      if (!dd.startsOutsideView) {
        if (!timeAxis.dateInAxis(startDate, false)) {
          const tick = timeAxis.getTickFromDate(startDate);
          if (tick >= 0) {
            startDate = timeAxis.getDateFromTick(tick);
          }
        }
        endDate = startDate && DateHelper.add(startDate, totalDurationMS);
      } else if (!dd.endsOutsideView) {
        startDate = endDate && DateHelper.add(endDate, -totalDurationMS);
      }
    }
    return {
      startDate,
      endDate,
    };
  }
  //endregion
  //region Dragtip
  /**
   * Gets html to display in tooltip while dragging event. Uses clockTemplate to display start & end dates.
   */
  getTipHtml() {
    const me = this,
      { dragData, client, tooltipTemplate } = me,
      { startDate, endDate, draggedEntities } = dragData,
      startText = client.getFormattedDate(startDate),
      endText =
        (endDate && client.getFormattedEndDate(endDate, startDate)) || "",
      { valid, message, element, dragProxy } = dragData.context,
      tipTarget = dragProxy ? dragProxy.firstChild : element,
      dragged = draggedEntities[0],
      timeSpanRecord = dragged.isTask ? dragged : dragged.event;
    me.tip.lastAlignSpec.target = tipTarget;
    return tooltipTemplate({
      valid,
      startDate,
      endDate,
      startText,
      endText,
      dragData,
      message: message || "",
      [client.scheduledEventName + "Record"]: timeSpanRecord,
      startClockHtml: me.clockTemplate.template({
        date: startDate,
        text: startText,
        cls: "b-sch-tooltip-startdate",
      }),
      endClockHtml: timeSpanRecord.isMilestone
        ? ""
        : me.clockTemplate.template({
            date: endDate,
            text: endText,
            cls: "b-sch-tooltip-enddate",
          }),
    });
  }
  //endregion
  //region Configurable
  // Constrain to time slot means lockX if we're horizontal, otherwise lockY
  updateConstrainDragToTimeSlot(value) {
    const axis = this.client.isHorizontal ? "lockX" : "lockY";
    if (this.drag) {
      this.drag[axis] = value;
    }
  }
  // Constrain to resource means lockY if we're horizontal, otherwise lockX
  updateConstrainDragToResource(constrainDragToResource) {
    const me = this;
    if (me.drag) {
      const { constrainDragToTimeSlot } = me,
        { isHorizontal } = me.client;
      if (constrainDragToResource) {
        me.constrainDragToTimeline = true;
      }
      me.drag.lockY = isHorizontal
        ? constrainDragToResource
        : constrainDragToTimeSlot;
      me.drag.lockX = isHorizontal
        ? constrainDragToTimeSlot
        : constrainDragToResource;
    }
  }
  updateConstrainDragToTimeline(constrainDragToTimeline) {
    if (!this.isConfiguring) {
      Object.assign(this.drag, {
        cloneTarget: !constrainDragToTimeline,
        allowDropOutside: !constrainDragToTimeline,
        dragWithin: constrainDragToTimeline ? null : this.client.floatRoot,
        scrollManager: constrainDragToTimeline
          ? this.client.scrollManager
          : null,
      });
    }
  }
  constrainStartDate(startDate) {
    const { dragData } = this,
      { dateConstraints } = dragData,
      scheduleableRecord =
        dragData.eventRecord ||
        dragData.taskRecord ||
        dragData.draggedEntities[0];
    if (dateConstraints == null ? void 0 : dateConstraints.start) {
      startDate = DateHelper.max(dateConstraints.start, startDate);
    }
    if (dateConstraints == null ? void 0 : dateConstraints.end) {
      startDate = DateHelper.min(
        new Date(dateConstraints.end - scheduleableRecord.durationMS),
        startDate,
      );
    }
    return startDate;
  }
  //endregion
  //region Product specific, implemented in subclasses
  getElementFromContext(context) {
    return context.grabbed || context.dragProxy || context.element;
  }
  // Provide your custom implementation of this to allow additional selected records to be dragged together with the original one.
  getRelatedRecords(record) {
    return [];
  }
  getMinimalDragData(info, event) {
    return {};
  }
  // Check if element can be dropped at desired location
  isValidDrop(dragData) {
    throw new Error("Implement in subclass");
  }
  // Similar to the fn above but also calls validatorFn
  checkDragValidity(dragData) {
    throw new Error("Implement in subclass");
  }
  // Update records being dragged
  updateRecords(context) {
    throw new Error("Implement in subclass");
  }
  // Determine if an element can be dragged
  isElementDraggable(el, event) {
    throw new Error("Implement in subclass");
  }
  // Get coordinate for correct axis
  getCoordinate(record, element, coord) {
    throw new Error("Implement in subclass");
  }
  // Product specific drag data
  setupProductDragData(info) {
    throw new Error("Implement in subclass");
  }
  // Product specific data in drag context
  getProductDragContext(dd) {
    throw new Error("Implement in subclass");
  }
  getRecordElement(record) {
    throw new Error("Implement in subclass");
  }
  //endregion
};
DragBase._$name = "DragBase";

// ../Scheduler/lib/Scheduler/feature/EventResize.js
var tipAlign = {
  top: "b-t",
  right: "b100-t100",
  bottom: "t-b",
  left: "b0-t0",
};
var EventResize = class extends InstancePlugin.mixin(
  Draggable_default,
  Droppable_default,
) {
  //region Events
  /**
   * Fired on the owning Scheduler before resizing starts. Return `false` to prevent the action.
   * @event beforeEventResize
   * @on-owner
   * @preventable
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.EventModel} eventRecord Event record being resized
   * @param {Scheduler.model.ResourceModel} resourceRecord Resource record the resize starts within
   * @param {MouseEvent} event Browser event
   */
  /**
   * Fires on the owning Scheduler when event resizing starts
   * @event eventResizeStart
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.EventModel} eventRecord Event record being resized
   * @param {Scheduler.model.ResourceModel} resourceRecord Resource record the resize starts within
   * @param {MouseEvent} event Browser event
   */
  /**
   * Fires on the owning Scheduler on each resize move event
   * @event eventPartialResize
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Scheduler.model.EventModel} eventRecord Event record being resized
   * @param {Date} startDate
   * @param {Date} endDate
   * @param {HTMLElement} element
   */
  /**
   * Fired on the owning Scheduler to allow implementer to prevent immediate finalization by setting
   * `data.context.async = true` in the listener, to show a confirmation popup etc
   *
   * ```javascript
   *  scheduler.on('beforeeventresizefinalize', ({context}) => {
   *      context.async = true;
   *      setTimeout(() => {
   *          // async code don't forget to call finalize
   *          context.finalize();
   *      }, 1000);
   *  })
   * ```
   *
   * @event beforeEventResizeFinalize
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Object} context
   * @param {Scheduler.model.EventModel} context.eventRecord Event record being resized
   * @param {Date} context.startDate New startDate (changed if resizing start side)
   * @param {Date} context.endDate New endDate (changed if resizing end side)
   * @param {Date} context.originalStartDate Start date before resize
   * @param {Date} context.originalEndDate End date before resize
   * @param {Boolean} context.async Set true to handle resize asynchronously (e.g. to wait for user confirmation)
   * @param {Function} context.finalize Call this method to finalize resize. This method accepts one argument:
   *                   pass `true` to update records, or `false`, to ignore changes
   * @param {Event} event Browser event
   */
  /**
   * Fires on the owning Scheduler after the resizing gesture has finished.
   * @event eventResizeEnd
   * @on-owner
   * @param {Scheduler.view.Scheduler} source Scheduler instance
   * @param {Boolean} changed Shows if the record has been changed by the resize action
   * @param {Scheduler.model.EventModel} eventRecord Event record being resized
   */
  //endregion
  //region Config
  static get $name() {
    return "EventResize";
  }
  static get configurable() {
    return {
      draggingItemCls: "b-sch-event-wrap-resizing",
      resizingItemInnerCls: "b-sch-event-resizing",
      /**
       * Use left handle when resizing. Only applies when owning client's `direction` is 'horizontal'
       * @config {Boolean}
       * @default
       */
      leftHandle: true,
      /**
       * Use right handle when resizing. Only applies when owning client's `direction` is 'horizontal'
       * @config {Boolean}
       * @default
       */
      rightHandle: true,
      /**
       * Use top handle when resizing. Only applies when owning client's direction` is 'vertical'
       * @config {Boolean}
       * @default
       */
      topHandle: true,
      /**
       * Use bottom handle when resizing. Only applies when owning client's `direction` is 'vertical'
       * @config {Boolean}
       * @default
       */
      bottomHandle: true,
      /**
       * Resizing handle size to use instead of that determined by CSS
       * @config {Number}
       * @deprecated Since 5.2.7. The handle size is determined from responsive CSS. Will be removed in 6.0
       */
      handleSize: null,
      /**
       * Automatically shrink virtual handles when available space < handleSize. The virtual handles will
       * decrease towards width/height 1, reserving space between opposite handles to for example leave room for
       * dragging. To configure reserved space, see {@link #config-reservedSpace}.
       * @config {Boolean}
       * @default false
       */
      dynamicHandleSize: true,
      /**
       * Set to true to allow resizing to a zero-duration span
       * @config {Boolean}
       * @default false
       */
      allowResizeToZero: null,
      /**
       * Room in px to leave unoccupied by handles when shrinking them dynamically (see
       * {@link #config-dynamicHandleSize}).
       * @config {Number}
       * @default
       */
      reservedSpace: 5,
      /**
       * Resizing handle size to use instead of that determined by CSS on touch devices
       * @config {Number}
       * @deprecated Since 5.2.7. The handle size is determined from responsive CSS. Will be removed in 6.0
       */
      touchHandleSize: null,
      /**
       * The amount of pixels to move pointer/mouse before it counts as a drag operation.
       * @config {Number}
       * @default
       */
      dragThreshold: 0,
      dragTouchStartDelay: 0,
      draggingClsSelector: ".b-timeline-base",
      /**
       * `false` to not show a tooltip while resizing
       * @config {Boolean}
       * @default
       */
      showTooltip: true,
      /**
       * true to see exact event length during resizing
       * @config {Boolean}
       * @default
       */
      showExactResizePosition: false,
      /**
       * An empty function by default, but provided so that you can perform custom validation on
       * the item being resized. Return true if the new duration is valid, false to signal that it is not.
       * @param {Object} context The resize context, contains the record & dates.
       * @param {Scheduler.model.TimeSpan} context.record The record being resized.
       * @param {Date} context.startDate The new start date.
       * @param {Date} context.endDate The new start date.
       * @param {Date} context.originalStartDate Start date before resize
       * @param {Date} context.originalEndDate End date before resize
       * @param {Event} event The browser Event object
       * @returns {Boolean}
       * @config {Function}
       */
      validatorFn: () => true,
      /**
       * `this` reference for the validatorFn
       * @config {Object}
       */
      validatorFnThisObj: null,
      /**
       * Setting this property may change the configuration of the {@link #config-tip}, or
       * cause it to be destroyed if `null` is passed.
       *
       * Reading this property returns the Tooltip instance.
       * @member {Core.widget.Tooltip|TooltipConfig} tip
       */
      /**
       * If a tooltip is required to illustrate the resize, specify this as `true`, or a config
       * object for the {@link Core.widget.Tooltip}.
       * @config {Core.widget.Tooltip|TooltipConfig}
       */
      tip: {
        $config: ["lazy", "nullify"],
        value: {
          autoShow: false,
          axisLock: true,
          trackMouse: false,
          updateContentOnMouseMove: true,
          hideDelay: 0,
        },
      },
      /**
       * A template function returning the content to show during a resize operation.
       *
       * @config {Function} tooltipTemplate
       * @param {Object} context A context object
       * @param {Date} context.startDate New start date
       * @param {Date} context.endDate New end date
       * @param {Scheduler.model.TimeSpan} context.record The record being resized
       * @param {String} context.startClockHtml Predefined HTML to show the start time
       * @param {String} context.endClockHtml Predefined HTML to show the end time
       * @returns {String} String representing the HTML markup
       */
      tooltipTemplate: (context) => `
                <div class="b-sch-tip-${context.valid ? "valid" : "invalid"}">
                    ${context.startClockHtml}
                    ${context.endClockHtml}
                    <div class="b-sch-tip-message">${context.message}</div>
                </div>
            `,
      ignoreSelector: ".b-sch-terminal",
      dragActiveCls: "b-resizing-event",
      /**
       * Locks the layout during drag resize, overriding the default behaviour that uses the same rendering
       * pathway for drag resize as for already existing events.
       *
       * This more closely resembles the behaviour of versions prior to 4.2.0.
       *
       * Enabling this config also leads to cheaper resizing, only the resized event's resources are refreshed
       * during the operation.
       *
       * {@note}Note that this will be the default behaviour starting with version 6.0.0{/@note}
       *
       * @config {Boolean}
       */
      lockLayout: VersionHelper.checkVersion("core", "6.0", ">="),
    };
  }
  static get pluginConfig() {
    return {
      chain: ["render", "onEventDataGenerated", "isEventElementDraggable"],
    };
  }
  //endregion
  //region Init & destroy
  doDestroy() {
    var _a4;
    super.doDestroy();
    (_a4 = this.dragging) == null ? void 0 : _a4.destroy();
  }
  render() {
    const me = this,
      { client } = me;
    me.dragSelector = me.dragItemSelector = client.eventSelector;
    me.dragRootElement = me.dropRootElement = client.timeAxisSubGridElement;
    me.dragLock = client.isVertical ? "y" : "x";
  }
  // Prevent event dragging when it happens over a resize handle
  isEventElementDraggable(eventElement, eventRecord, el, event) {
    const me = this,
      eventResizable = eventRecord == null ? void 0 : eventRecord.resizable;
    if (me.disabled || !eventResizable || eventRecord.isMilestone) {
      return true;
    }
    return (
      ((eventResizable !== true && eventResizable !== "start") ||
        !me.isOverStartHandle(event, eventElement)) &&
      ((eventResizable !== true && eventResizable !== "end") ||
        !me.isOverEndHandle(event, eventElement))
    );
  }
  // Called for each event during render, allows manipulation of render data.
  onEventDataGenerated({ eventRecord, wrapperCls, cls: cls2 }) {
    var _a4, _b;
    if (
      eventRecord ===
      ((_b = (_a4 = this.dragging) == null ? void 0 : _a4.context) == null
        ? void 0
        : _b.eventRecord)
    ) {
      wrapperCls["b-active"] =
        wrapperCls[this.draggingItemCls] =
        wrapperCls["b-over-resize-handle"] =
        cls2["b-resize-handle"] =
        cls2[this.resizingItemInnerCls] =
          1;
    }
  }
  // Sneak a first peek at the drag event to put necessary date values into the context
  onDragPointerMove(event) {
    var _a4;
    const { client, dragging } = this,
      { visibleDateRange, isHorizontal } = client,
      rtl = isHorizontal && client.rtl,
      dimension = isHorizontal ? "X" : "Y",
      pageScroll = globalThis[`page${dimension}Offset`],
      coord =
        event[`page${dimension}`] +
        (((_a4 = dragging.context) == null ? void 0 : _a4.offset) || 0),
      clientRect = Rectangle.from(client.timeAxisSubGridElement, null, true),
      startCoord = clientRect.getStart(rtl, isHorizontal),
      endCoord = clientRect.getEnd(rtl, isHorizontal);
    let date = client.getDateFromCoord({ coord, local: false });
    if (rtl) {
      if (coord - pageScroll > startCoord) {
        date = visibleDateRange.startDate;
      } else if (coord < endCoord) {
        date = visibleDateRange.endDate;
      }
    } else if (coord - pageScroll < startCoord) {
      date = visibleDateRange.startDate;
    } else if (coord - pageScroll > endCoord) {
      date = visibleDateRange.endDate;
    }
    dragging.clientStartCoord = startCoord;
    dragging.clientEndCoord = endCoord;
    dragging.date = date;
    super.onDragPointerMove(event);
  }
  /**
   * Returns true if a resize operation is active
   * @property {Boolean}
   * @readonly
   */
  get isResizing() {
    return Boolean(this.dragging);
  }
  beforeDrag(drag) {
    const { client } = this,
      eventRecord = client.resolveTimeSpanRecord(drag.itemElement),
      resourceRecord =
        !client.isGanttBase &&
        client.resolveResourceRecord(
          client.isVertical ? drag.startEvent : drag.itemElement,
        );
    if (
      this.disabled ||
      client.readOnly ||
      (resourceRecord == null ? void 0 : resourceRecord.readOnly) ||
      (eventRecord &&
        (eventRecord.readOnly ||
          !(eventRecord.project || eventRecord.isOccurrence))) ||
      super.beforeDrag(drag) === false
    ) {
      return false;
    }
    drag.mousedownDate = drag.date = client.getDateFromCoordinate(
      drag.event[`page${client.isHorizontal ? "X" : "Y"}`],
      null,
      false,
    );
    return this.triggerBeforeResize(drag);
  }
  dragStart(drag) {
    var _a4, _b;
    const me = this,
      { client, tip } = me,
      { startEvent, itemElement } = drag,
      name = client.scheduledEventName,
      eventRecord = client.resolveEventRecord(itemElement),
      { isBatchUpdating, wrapStartDate, wrapEndDate } = eventRecord,
      useEventBuffer =
        (_a4 = client.features.eventBuffer) == null ? void 0 : _a4.enabled,
      eventStartDate = isBatchUpdating
        ? eventRecord.get("startDate")
        : eventRecord.startDate,
      eventEndDate = isBatchUpdating
        ? eventRecord.get("endDate")
        : eventRecord.endDate,
      horizontal = me.dragLock === "x",
      rtl = horizontal && client.rtl,
      draggingEnd = me.isOverEndHandle(startEvent, itemElement),
      toSet = draggingEnd ? "endDate" : "startDate",
      wrapToSet = !useEventBuffer
        ? null
        : draggingEnd
          ? "wrapEndDate"
          : "wrapStartDate",
      otherEnd = draggingEnd ? "startDate" : "endDate",
      setMethod = draggingEnd ? "setEndDate" : "setStartDate",
      setOtherMethod = draggingEnd ? "setStartDate" : "setEndDate",
      elRect = Rectangle.from(itemElement),
      startCoord = horizontal ? startEvent.clientX : startEvent.clientY,
      endCoord = draggingEnd
        ? elRect.getEnd(rtl, horizontal)
        : elRect.getStart(rtl, horizontal),
      context = (drag.context = {
        eventRecord,
        element: itemElement,
        timespanRecord: eventRecord,
        taskRecord: eventRecord,
        owner: me,
        valid: true,
        oldValue: draggingEnd ? eventEndDate : eventStartDate,
        startDate: eventStartDate,
        endDate: eventEndDate,
        offset: useEventBuffer ? 0 : endCoord - startCoord,
        edge: horizontal
          ? draggingEnd
            ? "right"
            : "left"
          : draggingEnd
            ? "bottom"
            : "top",
        finalize: me.finalize,
        event: drag.event,
        // these two are public
        originalStartDate: eventStartDate,
        originalEndDate: eventEndDate,
        wrapStartDate,
        wrapEndDate,
        draggingEnd,
        toSet,
        wrapToSet,
        otherEnd,
        setMethod,
        setOtherMethod,
      });
    eventRecord.meta.isResizing = true;
    client.element.classList.add(...me.dragActiveCls.split(" "));
    if (!client.listenToBatchedUpdates) {
      client.beginListeningForBatchedUpdates();
    }
    if (!isBatchUpdating) {
      me.beginEventRecordBatch(eventRecord);
    }
    me.setupProductResizeContext(context, startEvent);
    me.triggerEventResizeStart(
      `${name}ResizeStart`,
      {
        [`${name}Record`]: eventRecord,
        event: startEvent,
        ...me.getResizeStartParams(context),
      },
      context,
    );
    context.resizedRecord =
      ((_b = client.resolveAssignmentRecord) == null
        ? void 0
        : _b.call(client, context.element)) || eventRecord;
    if (tip) {
      tip.show();
      tip.align = tipAlign[context.edge];
      tip.showBy(me.getTooltipTarget(drag));
    }
  }
  // Subclasses may override this
  triggerBeforeResize(drag) {
    const { client } = this,
      eventRecord = client.resolveTimeSpanRecord(drag.itemElement);
    return client.trigger(`before${client.capitalizedEventName}Resize`, {
      [`${client.scheduledEventName}Record`]: eventRecord,
      event: drag.event,
      ...this.getBeforeResizeParams({
        event: drag.startEvent,
        element: drag.itemElement,
      }),
    });
  }
  // Subclasses may override this
  triggerEventResizeStart(eventType, event, context) {
    var _a4, _b;
    this.client.trigger(eventType, event);
    (_b = (_a4 = this.client)[`after${StringHelper.capitalize(eventType)}`]) ==
    null
      ? void 0
      : _b.call(_a4, context, event);
  }
  triggerEventResizeEnd(eventType, event) {
    this.client.trigger(eventType, event);
  }
  triggerEventPartialResize(eventType, event) {
    this.client.trigger(eventType, event);
  }
  triggerBeforeEventResizeFinalize(eventType, event) {
    this.client.trigger(eventType, event);
  }
  dragEnter(drag) {
    var _a4;
    return ((_a4 = drag.context) == null ? void 0 : _a4.owner) === this;
  }
  resizeEventPartiallyInternal(eventRecord, context) {
    var _a4;
    const { client } = this,
      { toSet } = context;
    if ((_a4 = client.features.eventBuffer) == null ? void 0 : _a4.enabled) {
      if (toSet === "startDate") {
        const diff =
          context.startDate.getTime() - context.originalStartDate.getTime();
        eventRecord.wrapStartDate = new Date(
          context.wrapStartDate.getTime() + diff,
        );
      } else if (toSet === "endDate") {
        const diff =
          context.endDate.getTime() - context.originalEndDate.getTime();
        eventRecord.wrapEndDate = new Date(
          context.wrapEndDate.getTime() + diff,
        );
      }
    }
    eventRecord.set(toSet, context[toSet]);
  }
  applyDateConstraints(date, eventRecord, context) {
    var _a4, _b;
    const minDate =
        (_a4 = context.dateConstraints) == null ? void 0 : _a4.start,
      maxDate = (_b = context.dateConstraints) == null ? void 0 : _b.end;
    if (minDate || maxDate) {
      date = DateHelper.constrain(date, minDate, maxDate);
      context.snappedDate = DateHelper.constrain(
        context.snappedDate,
        minDate,
        maxDate,
      );
    }
    return date;
  }
  // Override the draggable interface so that we can update the bar while dragging outside
  // the Draggable's rootElement (by default it stops notifications when outside rootElement)
  moveDrag(drag) {
    const me = this,
      { client, tip } = me,
      horizontal = me.dragLock === "x",
      dimension = horizontal ? "X" : "Y",
      name = client.scheduledEventName,
      { visibleDateRange, enableEventAnimations, timeAxis, weekStartDay } =
        client,
      rtl = horizontal && client.rtl,
      { resolutionUnit, resolutionIncrement } = timeAxis,
      { event, context } = drag,
      { eventRecord, oldValue } = context,
      offset = context.offset * (rtl ? -1 : 1),
      { isOccurrence } = eventRecord,
      eventStart = eventRecord.get("startDate"),
      eventEnd = eventRecord.get("endDate"),
      coord = event[`client${dimension}`] + offset,
      clientRect = Rectangle.from(client.timeAxisSubGridElement, null, true),
      startCoord = clientRect.getStart(rtl, horizontal),
      endCoord = clientRect.getEnd(rtl, horizontal);
    context.event = event;
    if (event.isScroll) {
      drag.date = client.getDateFromCoordinate(
        event[`page${dimension}`] + offset,
        null,
        false,
      );
    }
    let crossedOver,
      avoidedZeroSize,
      { date } = drag,
      { toSet, otherEnd, draggingEnd } = context;
    if (rtl) {
      if (coord > startCoord) {
        date = drag.date = visibleDateRange.startDate;
      } else if (coord < endCoord) {
        date = drag.date = visibleDateRange.endDate;
      }
    } else if (coord < startCoord) {
      date = drag.date = visibleDateRange.startDate;
    } else if (coord > endCoord) {
      date = drag.date = visibleDateRange.endDate;
    }
    if (toSet === "endDate") {
      if (date < eventStart) {
        crossedOver = -1;
      }
    } else {
      if (date > eventEnd) {
        crossedOver = 1;
      }
    }
    if (crossedOver && me.onDragEndSwitch) {
      me.onDragEndSwitch(context, date, crossedOver);
      otherEnd = context.otherEnd;
      toSet = context.toSet;
    }
    if (client.snapRelativeToEventStartDate) {
      date = timeAxis.roundDate(date, oldValue);
    }
    context.snappedDate = DateHelper.round(
      date,
      timeAxis.resolution,
      null,
      weekStartDay,
    );
    const duration =
      DateHelper.diff(date, context[otherEnd], resolutionUnit) *
      (draggingEnd ? -1 : 1);
    if (me.isEventDragCreate) {
      context.tooNarrow = duration < resolutionIncrement / 2;
    } else if (duration < resolutionIncrement) {
      if (me.allowResizeToZero) {
        context.snappedDate = date = context[otherEnd];
      } else {
        const sign = otherEnd === "startDate" ? 1 : -1,
          snappedDate = timeAxis.roundDate(
            DateHelper.add(
              eventRecord.get(otherEnd),
              resolutionIncrement * sign,
              resolutionUnit,
            ),
          );
        if (
          (snappedDate - oldValue) * sign < 0 ||
          (date - oldValue) * sign > 0
        ) {
          date =
            sign > 0
              ? DateHelper.max(date, snappedDate)
              : DateHelper.min(date, snappedDate);
          context.snappedDate = snappedDate;
        } else {
          date =
            sign > 0
              ? DateHelper.max(date, oldValue)
              : DateHelper.min(date, oldValue);
          context.snappedDate = oldValue;
        }
        avoidedZeroSize = true;
      }
    }
    date = me.applyDateConstraints(date, eventRecord, context);
    if (!context.date || date - context.date || avoidedZeroSize) {
      context.date = date;
      context[toSet] =
        me.showExactResizePosition || client.timeAxisViewModel.snap
          ? context.snappedDate
          : date;
      context.valid =
        me.allowResizeToZero ||
        context[toSet] -
          context[toSet === "startDate" ? "endDate" : "startDate"] !==
          0;
      if (eventRecord.get(toSet) - context[toSet]) {
        context.valid = me.checkValidity(context, event);
        context.message = "";
        if (context.valid && typeof context.valid !== "boolean") {
          context.message = context.valid.message;
          context.valid = context.valid.valid;
        }
        context.valid = context.valid !== false;
        if (context.valid) {
          const partialResizeEvent = {
            [`${name}Record`]: eventRecord,
            startDate: eventStart,
            endDate: eventEnd,
            element: drag.itemElement,
            context,
          };
          partialResizeEvent[toSet] = context[toSet];
          me.triggerEventPartialResize(
            `${name}PartialResize`,
            partialResizeEvent,
          );
          if (isOccurrence) {
            eventRecord.stores = [client.eventStore];
          }
          client.enableEventAnimations = false;
          this.resizeEventPartiallyInternal(eventRecord, context);
          client.enableEventAnimations = enableEventAnimations;
          if (isOccurrence) {
            eventRecord.stores = null;
          }
        }
        if (context.tooNarrow) {
          context.valid = false;
        }
      }
    }
    if (tip) {
      tip.align = tipAlign[context.edge];
      tip.alignTo(me.getTooltipTarget(drag));
    }
    super.moveDrag(drag);
  }
  dragEnd(drag) {
    const { context } = drag;
    if (context) {
      context.event = drag.event;
    }
    if (drag.aborted) {
      context == null ? void 0 : context.finalize(false);
    } else if (
      !this.isEventDragCreate &&
      !drag.started &&
      !EventHelper.getPagePoint(drag.event).equals(
        EventHelper.getPagePoint(drag.startEvent),
      )
    ) {
      this.dragStart(drag);
      this.cleanup(drag.context, false);
    }
  }
  async dragDrop({ context, event }) {
    var _a4;
    context[context.toSet] = context.snappedDate;
    const { client } = this,
      { startDate, endDate } = context;
    let modified;
    (_a4 = this.tip) == null ? void 0 : _a4.hide();
    context.valid =
      startDate &&
      endDate &&
      (this.allowResizeToZero || endDate - startDate > 0) && // Input sanity check
      context[context.toSet] - context.oldValue && // Make sure dragged end changed
      context.valid !== false;
    if (context.valid) {
      this.triggerBeforeEventResizeFinalize(
        `before${client.capitalizedEventName}ResizeFinalize`,
        {
          context,
          event,
          [`${client.scheduledEventName}Record`]: context.eventRecord,
        },
      );
      modified = true;
    }
    if (!context.async) {
      await context.finalize(modified);
    }
  }
  // This is called with a thisObj of the context object
  // We set "me" to the owner, and "context" to the thisObj so that it
  // reads as if it were a method of this class.
  async finalize(updateRecord) {
    const me = this.owner,
      context = this,
      { eventRecord, oldValue, toSet } = context,
      { snapRelativeToEventStartDate, timeAxis } = me.client;
    if (context.finalizing) {
      return;
    }
    context.finalizing = true;
    let wasChanged = false;
    if (updateRecord) {
      if (snapRelativeToEventStartDate) {
        context[toSet] = context.snappedDate = timeAxis.roundDate(
          context.date,
          oldValue,
        );
      }
      wasChanged = await me.internalUpdateRecord(context, eventRecord);
    } else {
      me.cancelEventRecordBatch(eventRecord);
      if (eventRecord.isOccurrence) {
        eventRecord.resources.forEach((resource) =>
          me.client.repaintEventsForResource(resource),
        );
      }
    }
    if (!me.isDestroyed) {
      me.cleanup(context, wasChanged);
    }
  }
  // This is always called on drop or abort.
  cleanup(context, changed) {
    var _a4;
    const me = this,
      { client } = me,
      { element, eventRecord } = context,
      name = client.scheduledEventName;
    eventRecord.meta.isResizing = false;
    client.endListeningForBatchedUpdates();
    (_a4 = me.tip) == null ? void 0 : _a4.hide();
    me.unHighlightHandle(element);
    client.element.classList.remove(...me.dragActiveCls.split(" "));
    me.triggerEventResizeEnd(`${name}ResizeEnd`, {
      changed,
      [`${name}Record`]: eventRecord,
      ...me.getResizeEndParams(context),
    });
  }
  async internalUpdateRecord(context, timespanRecord) {
    var _a4;
    const { client } = this,
      { generation } = timespanRecord,
      { toSet, startDate, endDate, draggingEnd } = context;
    if (timespanRecord.isOccurrence) {
      client.endListeningForBatchedUpdates();
      timespanRecord[
        timespanRecord.batching > 1 ? "endBatch" : "cancelBatch"
      ]();
      timespanRecord.set(
        TimeSpan.prototype.inSetNormalize.call(timespanRecord, {
          startDate,
          endDate,
        }),
      );
    } else {
      const batchChanges = Object.assign({}, timespanRecord.meta.batchChanges);
      delete batchChanges[toSet];
      delete batchChanges.duration;
      if (timespanRecord.isEntity) {
        const duration = timespanRecord.run(
          "calculateProjectedDuration",
          startDate,
          endDate,
        );
        timespanRecord.set({
          // Fix the dragged date point according to the Entity's rules.
          [toSet]: timespanRecord.run(
            "calculateProjectedXDateWithDuration",
            draggingEnd ? startDate : endDate,
            draggingEnd,
            duration,
          ),
          [context.otherEnd]: context[context.otherEnd],
        });
      }
      client.endListeningForBatchedUpdates();
      this.cancelEventRecordBatch(timespanRecord);
      if ((_a4 = client.features.eventBuffer) == null ? void 0 : _a4.enabled) {
        timespanRecord[context.wrapToSet] = null;
      }
      timespanRecord[context.setMethod](context[toSet], false);
      if (Object.keys(batchChanges).length) {
        timespanRecord.set(batchChanges);
      }
    }
    await client.project.commitAsync();
    return timespanRecord.generation !== generation;
  }
  onDragItemMouseMove(event) {
    if (event.pointerType !== "touch" && !this.handleSelector) {
      this.checkResizeHandles(event);
    }
  }
  /**
   * Check if mouse is over a resize handle (virtual). If so, highlight.
   * @private
   * @param {MouseEvent} event
   */
  checkResizeHandles(event) {
    const me = this,
      { overItem } = me;
    if (
      overItem &&
      !me.client.readOnly &&
      (!me.allowResize || me.allowResize(overItem, event))
    ) {
      const eventRecord = me.client.resolveTimeSpanRecord(overItem);
      if (eventRecord == null ? void 0 : eventRecord.readOnly) {
        return;
      }
      if (me.isOverAnyHandle(event, overItem)) {
        me.highlightHandle();
      } else {
        me.unHighlightHandle();
      }
    }
  }
  onDragItemMouseLeave(event, oldOverItem) {
    this.unHighlightHandle(oldOverItem);
  }
  /**
   * Highlights handles (applies css that changes cursor).
   * @private
   */
  highlightHandle() {
    var _a4, _b;
    const { overItem: item, client } = this,
      handleTargetElement =
        (_b =
          (_a4 = item.syncIdMap) == null
            ? void 0
            : _a4[client.scheduledEventName]) != null
          ? _b
          : item.querySelector(client.eventInnerSelector);
    handleTargetElement.classList.add("b-resize-handle");
    item.classList.add("b-over-resize-handle");
  }
  /**
   * Unhighlight handles (removes css).
   * @private
   */
  unHighlightHandle(item = this.overItem) {
    var _a4, _b;
    if (item) {
      const me = this,
        inner =
          (_b =
            (_a4 = item.syncIdMap) == null
              ? void 0
              : _a4[me.client.scheduledEventName]) != null
            ? _b
            : item.querySelector(me.client.eventInnerSelector);
      if (inner) {
        inner.classList.remove("b-resize-handle", me.resizingItemInnerCls);
      }
      item.classList.remove("b-over-resize-handle", me.draggingItemCls);
    }
  }
  isOverAnyHandle(event, target) {
    return Boolean(
      this.isOverStartHandle(event, target) ||
      this.isOverEndHandle(event, target),
    );
  }
  isOverStartHandle(event, target) {
    var _a4;
    return Boolean(
      (_a4 = this.getHandleRect("start", event, target)) == null
        ? void 0
        : _a4.contains(EventHelper.getPagePoint(event)),
    );
  }
  isOverEndHandle(event, target) {
    var _a4;
    return Boolean(
      (_a4 = this.getHandleRect("end", event, target)) == null
        ? void 0
        : _a4.contains(EventHelper.getPagePoint(event)),
    );
  }
  getHandleRect(side, event, eventEl) {
    if (this.overItem) {
      eventEl =
        event.target.closest(`.${this.client.eventCls}`) ||
        eventEl.querySelector(`.${this.client.eventCls}`);
      if (!eventEl) {
        return;
      }
      const me = this,
        start = side === "start",
        { client } = me,
        rtl = Boolean(client.rtl),
        axis = me.dragLock,
        horizontal = axis === "x",
        dim = horizontal ? "width" : "height",
        handleSpec = `${horizontal ? (start && !rtl ? "left" : "right") : start ? "top" : "bottom"}Handle`,
        { offsetWidth } = eventEl,
        timespanRecord = client.resolveTimeSpanRecord(eventEl),
        resizable =
          timespanRecord == null ? void 0 : timespanRecord.isResizable,
        eventRect = Rectangle.from(eventEl),
        result = eventRect.clone(),
        handleStyle = globalThis.getComputedStyle(eventEl, ":before"),
        touchHandleSize =
          !me.handleSelector && !BrowserHelper.isHoverableDevice
            ? me.touchHandleSize
            : void 0,
        handleSize =
          touchHandleSize || me.handleSize || parseFloat(handleStyle[dim]),
        handleVisThresh = me.handleVisibilityThreshold || 2 * me.handleSize,
        centerGap = me.dynamicHandleSize ? me.reservedSpace / 2 : 0,
        deflateArgs = [0, 0, 0, 0];
      if (
        !me.disabled &&
        me[handleSpec] &&
        (offsetWidth >= handleVisThresh || me.dynamicHandleSize) &&
        (resizable === true || resizable === side)
      ) {
        const oppositeEnd =
          (!horizontal && !start) || (horizontal && rtl === start);
        if (oppositeEnd) {
          result[axis] += eventRect[dim] - handleSize;
          deflateArgs[horizontal ? 3 : 0] = eventRect[dim] / 2 + centerGap;
        } else {
          deflateArgs[horizontal ? 1 : 2] = eventRect[dim] / 2 + centerGap;
        }
        eventRect.deflate(...deflateArgs);
        result[dim] = handleSize;
        result.constrainTo(eventRect);
        if (result[dim]) {
          return result;
        }
      }
    }
  }
  setupDragContext(event) {
    const me = this;
    if (
      me.overItem &&
      me.isOverAnyHandle(event, me.overItem) &&
      me.isElementResizable(me.overItem, event)
    ) {
      const result = super.setupDragContext(event);
      result.scrollManager = me.client.scrollManager;
      return result;
    }
  }
  changeHandleSize() {
    VersionHelper.deprecate("Scheduler", "6.0.0", "Handle size is from CSS");
  }
  changeTouchHandleSize() {
    VersionHelper.deprecate("Scheduler", "6.0.0", "Handle size is from CSS");
  }
  changeTip(tip, oldTip) {
    var _a4;
    const me = this;
    if (!me.showTooltip) {
      return null;
    }
    if (tip) {
      if (tip.isTooltip) {
        tip.owner = me;
      } else {
        tip = Tooltip.reconfigure(
          oldTip,
          Tooltip.mergeConfigs(
            {
              id: me.tipId,
            },
            tip,
            {
              getHtml: me.getTipHtml.bind(me),
              owner: me.client,
            },
            me.tip,
          ),
          {
            owner: me,
            defaults: {
              type: "tooltip",
            },
          },
        );
      }
      tip.ion({
        innerhtmlupdate: "updateDateIndicator",
        thisObj: me,
      });
      me.clockTemplate = new ClockTemplate({
        scheduler: me.client,
      });
    } else if (oldTip) {
      oldTip.destroy();
      (_a4 = me.clockTemplate) == null ? void 0 : _a4.destroy();
    }
    return tip;
  }
  //endregion
  //region Events
  isElementResizable(element, event) {
    var _a4;
    const me = this,
      { client } = me,
      timespanRecord = client.resolveTimeSpanRecord(element);
    if (client.readOnly) {
      return false;
    }
    let resizable =
      timespanRecord == null ? void 0 : timespanRecord.isResizable;
    const handleHoldingElement =
        (_a4 =
          element == null
            ? void 0
            : element.syncIdMap[client.scheduledEventName]) != null
          ? _a4
          : element,
      handleEl = event.target.closest('[class$="-handle"]');
    if (!resizable || (handleEl && handleEl !== handleHoldingElement)) {
      return false;
    }
    element = event.target.closest(me.dragSelector);
    if (!element) {
      return false;
    }
    const startsOutside = element.classList.contains(
        "b-sch-event-startsoutside",
      ),
      endsOutside = element.classList.contains("b-sch-event-endsoutside");
    if (resizable === true) {
      if (startsOutside && endsOutside) {
        return false;
      } else if (startsOutside) {
        resizable = "end";
      } else if (endsOutside) {
        resizable = "start";
      } else {
        return (
          me.isOverStartHandle(event, element) ||
          me.isOverEndHandle(event, element)
        );
      }
    }
    if (
      (startsOutside && resizable === "start") ||
      (endsOutside && resizable === "end")
    ) {
      return false;
    }
    if (
      (me.isOverStartHandle(event, element) && resizable === "start") ||
      (me.isOverEndHandle(event, element) && resizable === "end")
    ) {
      return true;
    }
    return false;
  }
  updateDateIndicator() {
    const { clockTemplate } = this,
      { eventRecord, draggingEnd, snappedDate } = this.dragging.context,
      startDate = draggingEnd ? eventRecord.get("startDate") : snappedDate,
      endDate = draggingEnd ? snappedDate : eventRecord.get("endDate"),
      { element } = this.tip;
    clockTemplate.updateDateIndicator(
      element.querySelector(".b-sch-tooltip-startdate"),
      startDate,
    );
    clockTemplate.updateDateIndicator(
      element.querySelector(".b-sch-tooltip-enddate"),
      endDate,
    );
  }
  getTooltipTarget({ itemElement, context }) {
    const me = this,
      { rtl } = me.client,
      target = Rectangle.from(itemElement, null, true);
    if (me.dragLock === "x") {
      if (
        (!rtl && context.edge === "right") ||
        (rtl && context.edge === "left")
      ) {
        target.x = target.right - 1;
      } else {
        target.x -= me.tip.anchorSize[0] / 2;
      }
      target.width = me.tip.anchorSize[0] / 2;
    } else {
      if (context.edge === "bottom") {
        target.y = target.bottom - 1;
      }
      target.height = me.tip.anchorSize[1] / 2;
    }
    return { target };
  }
  basicValidityCheck(context, event) {
    return (
      context.startDate &&
      (context.endDate > context.startDate || this.allowResizeToZero) &&
      this.validatorFn.call(this.validatorFnThisObj || this, context, event)
    );
  }
  //endregion
  //region Tooltip
  getTipHtml({ tip }) {
    const me = this,
      {
        startDate,
        endDate,
        toSet,
        snappedDate,
        valid,
        message = "",
        timespanRecord,
      } = me.dragging.context;
    if (!startDate || !endDate) {
      return tip.html;
    }
    const tipData = {
      record: timespanRecord,
      valid,
      message,
      startDate,
      endDate,
      [toSet]: snappedDate,
    };
    tipData.startText = me.client.getFormattedDate(tipData.startDate);
    tipData.endText = me.client.getFormattedDate(tipData.endDate);
    tipData.startClockHtml = me.clockTemplate.template({
      date: tipData.startDate,
      text: tipData.startText,
      cls: "b-sch-tooltip-startdate",
    });
    tipData.endClockHtml = me.clockTemplate.template({
      date: tipData.endDate,
      text: tipData.endText,
      cls: "b-sch-tooltip-enddate",
    });
    return me.tooltipTemplate(tipData);
  }
  //endregion
  //region Product specific, may be overridden in subclasses
  beginEventRecordBatch(eventRecord) {
    eventRecord.beginBatch();
  }
  cancelEventRecordBatch(eventRecord) {
    eventRecord.cancelBatch();
  }
  getBeforeResizeParams(context) {
    const { client } = this;
    return {
      resourceRecord: client.resolveResourceRecord(
        client.isVertical ? context.event : context.element,
      ),
    };
  }
  getResizeStartParams(context) {
    return {
      resourceRecord: context.resourceRecord,
    };
  }
  getResizeEndParams(context) {
    return {
      resourceRecord: context.resourceRecord,
      event: context.event,
    };
  }
  setupProductResizeContext(context, event) {
    var _a4, _b, _c;
    const { client } = this,
      { element } = context,
      eventRecord = client.resolveEventRecord(element),
      resourceRecord =
        (_a4 = client.resolveResourceRecord) == null
          ? void 0
          : _a4.call(client, element),
      assignmentRecord =
        (_b = client.resolveAssignmentRecord) == null
          ? void 0
          : _b.call(client, element);
    Object.assign(context, {
      eventRecord,
      taskRecord: eventRecord,
      resourceRecord,
      assignmentRecord,
      dateConstraints:
        (_c = client.getDateConstraints) == null
          ? void 0
          : _c.call(client, resourceRecord, eventRecord),
    });
  }
  checkValidity({ startDate, endDate, eventRecord, resourceRecord }) {
    const { client } = this;
    if (!client.allowOverlap) {
      if (
        eventRecord.resources.some(
          (resource) =>
            !client.isDateRangeAvailable(
              startDate,
              endDate,
              eventRecord,
              resource,
            ),
        )
      ) {
        return {
          valid: false,
          message: this.L("L{EventDrag.eventOverlapsExisting}"),
        };
      }
    }
    return this.basicValidityCheck(...arguments);
  }
  get tipId() {
    return `${this.client.id}-event-resize-tip`;
  }
  //endregion
};
EventResize._$name = "EventResize";
GridFeatureManager.registerFeature(EventResize, true, "Scheduler");
GridFeatureManager.registerFeature(EventResize, false, "ResourceHistogram");

// ../Scheduler/lib/Scheduler/feature/mixin/TaskEditStm.js
var TaskEditStm_default = (Target) =>
  class TaskEditStm extends (Target || Base) {
    static get $name() {
      return "TaskEditStm";
    }
    getStmCapture() {
      return {
        stmInitiallyAutoRecord: this.stmInitiallyAutoRecord,
        stmInitiallyDisabled: this.stmInitiallyDisabled,
        // this flag indicates whether the STM capture has been transferred to
        // another feature, which will be responsible for finalizing the STM transaction
        // (otherwise we'll do it ourselves)
        transferred: false,
      };
    }
    applyStmCapture(stmCapture) {
      this.stmInitiallyAutoRecord = stmCapture.stmInitiallyAutoRecord;
      this.stmInitiallyDisabled = stmCapture.stmInitiallyDisabled;
    }
    captureStm(startTransaction = false) {
      const me = this,
        project = me.project,
        stm = project.getStm();
      if (me.hasStmCapture) {
        return;
      }
      me.hasStmCapture = true;
      me.stmInitiallyDisabled = stm.disabled;
      me.stmInitiallyAutoRecord = stm.autoRecord;
      if (me.stmInitiallyDisabled) {
        stm.enable();
        stm.autoRecord = false;
      } else {
        if (me.stmInitiallyAutoRecord) {
          stm.autoRecord = false;
        }
        if (stm.isRecording) {
          stm.stopTransaction();
        }
      }
      if (startTransaction) {
        this.startStmTransaction();
      }
    }
    startStmTransaction() {
      this.project.getStm().startTransaction();
    }
    commitStmTransaction() {
      const me = this,
        stm = me.project.getStm();
      if (!me.hasStmCapture) {
        throw new Error("Does not have STM capture, no transaction to commit");
      }
      if (stm.enabled) {
        stm.stopTransaction();
        if (me.stmInitiallyDisabled) {
          stm.resetQueue();
        }
      }
    }
    async rejectStmTransaction() {
      var _a4;
      const stm = this.project.getStm(),
        { client } = this;
      if (!this.hasStmCapture) {
        throw new Error("Does not have STM capture, no transaction to reject");
      }
      if (stm.enabled) {
        if ((_a4 = stm.transaction) == null ? void 0 : _a4.length) {
          client.suspendRefresh();
          stm.rejectTransaction();
          await client.resumeRefresh(true);
        } else {
          stm.stopTransaction();
        }
      }
    }
    enableStm() {
      this.project.getStm().enable();
    }
    disableStm() {
      this.project.getStm().disable();
    }
    async freeStm(commitOrReject = null) {
      const me = this,
        stm = me.project.getStm(),
        { stmInitiallyDisabled, stmInitiallyAutoRecord } = me;
      if (!me.hasStmCapture) {
        return;
      }
      let promise;
      me.rejectingStmTransaction = true;
      if (commitOrReject === true) {
        promise = me.commitStmTransaction();
      } else if (commitOrReject === false) {
        promise = me.rejectStmTransaction();
      }
      await promise;
      if (!stm.isDestroying) {
        stm.disabled = stmInitiallyDisabled;
        stm.autoRecord = stmInitiallyAutoRecord;
      }
      if (!me.isDestroying) {
        me.rejectingStmTransaction = true;
        me.hasStmCapture = false;
      }
    }
  };

// ../Scheduler/lib/Scheduler/feature/mixin/TaskEditTransactional.js
var TaskEditTransactional_default = (Target) =>
  class TaskEditTransactional extends (Target || Base) {
    static get $name() {
      return "TaskEditTransactional";
    }
    captureStm(force) {
      if (this.client.transactionalFeaturesEnabled) {
        super.captureStm();
        return this.startStmTransaction(force);
      } else {
        super.captureStm(force);
      }
    }
    freeStm(commitOrReject) {
      if (this.hasStmCapture || !this.client.transactionalFeaturesEnabled) {
        return super.freeStm(commitOrReject);
      }
    }
    async startStmTransaction(startRecordingEarly) {
      if (this.client.transactionalFeaturesEnabled) {
        await this.startFeatureTransaction(startRecordingEarly);
      } else {
        super.startStmTransaction();
      }
    }
    commitStmTransaction() {
      if (this.client.transactionalFeaturesEnabled) {
        return this.finishFeatureTransaction();
      } else {
        super.commitStmTransaction();
      }
    }
    async rejectStmTransaction() {
      if (this.client.transactionalFeaturesEnabled) {
        this.rejectFeatureTransaction();
      } else {
        await super.rejectStmTransaction();
      }
    }
  };

// ../Scheduler/lib/Scheduler/feature/mixin/TransactionalFeature.js
var TransactionalFeature_default = (Target) => {
  var _a4;
  return (
    (_a4 = class extends AttachToProjectMixin_default(Target || Base) {
      //#region AttachToProjectMixin implementation
      detachFromProject(project) {
        this.rejectFeatureTransaction();
        super.detachFromProject(project);
      }
      //#endregion
      getStmCapture() {
        const result = super.getStmCapture();
        result._editorPromiseResolve = this._editorPromiseResolve;
        return result;
      }
      applyStmCapture(stmCapture) {
        super.applyStmCapture(stmCapture);
        this._editorPromiseResolve = stmCapture._editorPromiseResolve;
      }
      async startFeatureTransaction() {
        var _a5, _b;
        if (!this.client.transactionalFeaturesEnabled) {
          return;
        }
        const me = this,
          { project } = me.client,
          { stm } = project,
          id = (me._featureTransactionId =
            IdHelper.generateId("featureTransaction"));
        (_b = (_a5 = me.client).trigger) == null
          ? void 0
          : _b.call(_a5, "beforeFeatureTransactionStart", { id });
        let chainResolved;
        if (me.hasStmCapture) {
          stm.startTransaction();
        } else {
          chainResolved = project.queue(async () => {
            if (!project.isEngineReady()) {
              await project.commitAsync();
            }
          });
        }
        project.queue(() => {
          var _a6, _b2;
          if (!me.hasStmCapture) {
            me._stmInitiallyDisabled = stm.disabled;
            me._stmInitiallyAutoRecord = stm.autoRecord;
            if (stm.isRecording) {
              stm.stopTransaction();
            } else if (me._stmInitiallyDisabled) {
              stm.enable();
            }
            stm.autoRecord = false;
          }
          if (!stm.isRecording) {
            stm.startTransaction();
          }
          (_b2 = (_a6 = me.client).trigger) == null
            ? void 0
            : _b2.call(_a6, "featureTransactionStart", { id });
          return new Promise((resolve) => (me._editorPromiseResolve = resolve));
        });
        await chainResolved;
      }
      rejectFeatureTransaction() {
        var _a5;
        const me = this,
          { stm } = me.client.project,
          id = me._featureTransactionId;
        if (!id || me.finishingFeatureTransaction) {
          return;
        }
        (_a5 = me._editorPromiseResolve) == null ? void 0 : _a5.call(me);
        me._editorPromiseResolve = null;
        delete me._featureTransactionId;
        stm.isRecording && stm.rejectTransaction();
        if (!me.hasStmCapture && me._stmInitiallyDisabled != null) {
          stm.disabled = me._stmInitiallyDisabled;
          stm.autoRecord = me._stmInitiallyAutoRecord;
        }
        me.client.trigger("featureTransactionReject", { id });
        me.client.trigger("featureTransactionComplete", { id });
      }
      async finishFeatureTransaction(afterApplyStashCallback) {
        var _a5;
        const me = this,
          { project } = me.client,
          { stm } = project,
          id = me._featureTransactionId;
