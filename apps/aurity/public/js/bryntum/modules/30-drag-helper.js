
// ../Core/lib/Core/helper/DragHelper.js
var rootElementListeners = {
  move: "onMouseMove",
  up: "onMouseUp",
  docclick: "onDocumentClick",
  touchstart: "onTouchStart",
  touchmove: "onTouchMove",
  touchend: "onTouchEnd",
  keydown: "onKeyDown",
};
var DragHelper = class extends Base.mixin(
  Events_default,
  DragHelperContainer_default,
  DragHelperTranslate_default,
) {
  //region Config
  static get defaultConfig() {
    return {
      /**
       * Drag proxy CSS class
       * @config {String}
       * @default
       * @private
       */
      dragProxyCls: "b-drag-proxy",
      /**
       * CSS class added when drag is invalid
       * @config {String}
       * @default
       */
      invalidCls: "b-drag-invalid",
      /**
       * CSS class added to the source element in Container drag
       * @config {String}
       * @default
       * @private
       */
      draggingCls: "b-dragging",
      /**
       * CSS class added to the source element in Container drag
       * @config {String}
       * @default
       * @private
       */
      dropPlaceholderCls: "b-drop-placeholder",
      /**
       * The amount of pixels to move mouse before it counts as a drag operation
       * @config {Number}
       * @default
       */
      dragThreshold: 5,
      /**
       * The outer element where the drag helper will operate (attach events to it and use as outer limit when looking for ancestors)
       * @config {HTMLElement}
       * @default
       */
      outerElement: document.body,
      /**
       * Outer element that limits where element can be dragged
       * @config {HTMLElement}
       */
      dragWithin: null,
      /**
       * Set to true to stack any related dragged elements below the main drag proxy element. Only applicable when
       * using translate {@link #config-mode} with {@link #config-cloneTarget}
       * @config {Boolean}
       */
      unifiedProxy: null,
      monitoringConfig: null,
      /**
       * Constrain translate drag to dragWithin elements bounds (set to false to allow it to "overlap" edges)
       * @config {Boolean}
       * @default
       */
      constrain: true,
      /**
       * Smallest allowed x when dragging horizontally.
       * @config {Number}
       */
      minX: null,
      /**
       * Largest allowed x when dragging horizontally.
       * @config {Number}
       */
      maxX: null,
      /**
       * Smallest allowed y when dragging horizontally.
       * @config {Number}
       */
      minY: null,
      /**
       * Largest allowed y when dragging horizontally.
       * @config {Number}
       */
      maxY: null,
      /**
       * Enabled dragging, specify mode:
       * <table>
       * <tr><td>container<td>Allows reordering elements within one and/or between multiple containers
       * <tr><td>translateXY<td>Allows dragging within a parent container
       * </table>
       * @config {'container'|'translateXY'}
       * @default
       */
      mode: "translateXY",
      /**
       * A function that determines if dragging an element is allowed. Gets called with the element as argument,
       * return `true` to allow dragging or `false` to prevent.
       * @config {Function}
       * @param {HTMLElement} element
       * @returns {Boolean}
       */
      isElementDraggable: null,
      /**
       * A CSS selector used to determine if dragging an element is allowed.
       * @config {String}
       */
      targetSelector: null,
      /**
       * A CSS selector used to determine if a drop is allowed at the current position.
       * @config {String}
       */
      dropTargetSelector: null,
      /**
       * A CSS selector added to each drop target element while dragging.
       * @config {String}
       */
      dropTargetCls: null,
      /**
       * A CSS selector used to target a child element of the mouse down element, to use as the drag proxy element.
       * Applies to translate {@link #config-mode mode} when using {@link #config-cloneTarget}.
       * @config {String}
       */
      proxySelector: null,
      /**
       * Set to `true` to clone the dragged target, and not move the actual target DOM node.
       * @config {Boolean}
       * @default
       */
      cloneTarget: false,
      /**
       * Set to `false` to not apply width/height of cloned drag proxy elements.
       * @config {Boolean}
       * @default
       */
      autoSizeClonedTarget: true,
      /**
       * Set to true to hide the original element while dragging (applicable when `cloneTarget` is true).
       * @config {Boolean}
       * @default
       */
      hideOriginalElement: false,
      /**
       * Containers whose elements can be rearranged (and moved between the containers). Used when
       * mode is set to "container".
       * @config {HTMLElement[]}
       */
      containers: null,
      /**
       * A CSS selector used to exclude elements when using container mode
       * @config {String}
       */
      ignoreSelector: null,
      startEvent: null,
      /**
       * Configure as `true` to disallow dragging in the `X` axis. The dragged element will only move vertically.
       * @config {Boolean}
       * @default
       */
      lockX: false,
      /**
       * Configure as `true` to disallow dragging in the `Y` axis. The dragged element will only move horizontally.
       * @config {Boolean}
       * @default
       */
      lockY: false,
      /**
       * The amount of milliseconds to wait after a touchstart, before a drag gesture will be allowed to start.
       * @config {Number}
       * @default
       */
      touchStartDelay: 300,
      /**
       * Scroll manager of the target. If specified, scrolling while dragging is supported.
       * @config {Core.util.ScrollManager}
       */
      scrollManager: null,
      /**
       * A method provided to snap coordinates to fixed points as you drag
       * @config {Function}
       * @internal
       */
      snapCoordinates: null,
      /**
       * When using {@link #config-unifiedProxy}, use this amount of pixels to offset each extra element when dragging multiple items
       * @config {Number}
       * @default
       */
      unifiedOffset: 5,
      /**
       * Configure as `false` to take ownership of the proxy element after a valid drop (advanced usage).
       * @config {Boolean}
       * @default
       */
      removeProxyAfterDrop: true,
      clickSwallowDuration: 50,
      ignoreSamePositionDrop: true,
      // true to allow drops outside the dragWithin element
      allowDropOutside: null,
      // for container mode
      floatRootOwner: null,
      mouseMoveListenerElement: document,
      externalDropTargetSelector: null,
      testConfig: {
        transitionDuration: 10,
        clickSwallowDuration: 50,
        touchStartDelay: 100,
      },
      rtlSource: null,
      /**
       * Creates the proxy element to be dragged, when using {@link #config-cloneTarget}. Clones the original element by default.
       * Provide your custom {@link #function-createProxy} function to be used for creating drag proxy.
       * @param {HTMLElement} element The element from which the drag operation originated
       * @config {Function}
       * @returns {HTMLElement}
       */
      createProxy: null,
    };
  }
  //endregion
  //region Events
  /**
   * Fired before dragging starts, return `false` to prevent the drag operation.
   * @preventable
   * @event beforeDragStart
   * @param {Core.helper.DragHelper} source
   * @param {Object} context
   * @param {HTMLElement} context.element The original element upon which the mousedown event triggered a drag operation
   * @param {MouseEvent|TouchEvent} event
   */
  /**
   * Fired when dragging starts. The event includes a `context` object. If you want to drag additional elements you can
   * provide these as an array of elements assigned to the `relatedElements` property of the context object.
   * @event dragStart
   * @param {Core.helper.DragHelper} source
   * @param {Object} context
   * @param {HTMLElement} context.element The element which we're moving, could be a cloned version of grabbed, or the grabbed element itself
   * @param {HTMLElement} context.grabbed The original element upon which the mousedown event triggered a drag operation
   * @param {HTMLElement[]} context.relatedElements Array of extra elements to include in the drag.
   * @param {MouseEvent|TouchEvent} event
   */
  /**
   * Fired while dragging, you can signal that the drop is valid or invalid by setting `context.valid = false;`
   * @event drag
   * @param {Core.helper.DragHelper} source
   * @param {Object} context
   * @param {HTMLElement} context.element The element which we are moving, could be a cloned version of grabbed, or the grabbed element itself
   * @param {HTMLElement} context.target The target element below the cursor
   * @param {HTMLElement} context.grabbed The original element upon which the mousedown event triggered a drag operation
   * @param {HTMLElement[]} context.relatedElements An array of extra elements dragged with the main dragged element
   * @param {Boolean} context.valid Set this to true or false to indicate whether the drop position is valid.
   * @param {MouseEvent} event
   */
  /**
   * Fired after a drop at an invalid position
   * @event abort
   * @param {Core.helper.DragHelper} source
   * @param {Object} context
   * @param {HTMLElement} context.element The element which we are moving, could be a cloned version of grabbed, or the grabbed element itself
   * @param {HTMLElement} context.target The target element below the cursor
   * @param {HTMLElement} context.grabbed The original element upon which the mousedown event triggered a drag operation
   * @param {HTMLElement[]} context.relatedElements An array of extra elements dragged with the main dragged element
   * @param {MouseEvent} event
   */
  /**
   * Fires after {@link #event-abort} and after drag proxy has animated back to its original position
   * @private
   * @event abortFinalized
   * @param {Core.helper.DragHelper} source
   * @param {Object} context
   * @param {HTMLElement} context.element The element which we are moving, could be a cloned version of grabbed, or the grabbed element itself
   * @param {HTMLElement} context.target The target element below the cursor
   * @param {HTMLElement} context.grabbed The original element upon which the mousedown event triggered a drag operation
   * @param {MouseEvent} event
   */
  //endregion
  //region Init
  /**
   * Initializes a new DragHelper.
   * @param {DragHelperConfig} config Configuration object, accepts options specified under Configs above
   *
   * ```javascript
   * new DragHelper({
   *   containers: [div1, div2],
   *   isElementDraggable: element => element.className.contains('handle'),
   *   outerElement: topParent,
   *   listeners: {
   *     drop: onDrop,
   *     thisObj: this
   *   }
   * });
   * ```
   *
   * @function constructor
   */
  construct(config) {
    const me = this;
    super.construct(config);
    me.initListeners();
    if (me.isContainerDrag) {
      me.initContainerDrag();
    } else {
      me.initTranslateDrag();
    }
    me.onScrollManagerScrollCallback =
      me.onScrollManagerScrollCallback.bind(me);
  }
  doDestroy() {
    this.reset(true);
    super.doDestroy();
  }
  /**
   * Initialize listener
   * @private
   */
  initListeners() {
    const me = this,
      { outerElement } = me,
      dragStartListeners = {
        element: outerElement,
        pointerdown: "onPointerDown",
        thisObj: me,
      };
    me.mouseMoveListenerElement = me.getMouseMoveListenerTarget(outerElement);
    EventHelper.on(dragStartListeners);
  }
  // Salesforce hook: we override this method to move listener from the body (which is default root node) to element
  // inside of LWC
  getMouseMoveListenerTarget(element) {
    const root = element.getRootNode();
    let result = this.mouseMoveListenerElement;
    if (
      root.nodeType === Node.DOCUMENT_FRAGMENT_NODE &&
      root.mode === "closed"
    ) {
      result = element.closest(".b-outer") || result;
    }
    return result;
  }
  get isRTL() {
    var _a4;
    return Boolean((_a4 = this.rtlSource) == null ? void 0 : _a4.rtl);
  }
  //endregion
  //region Events
  /**
   * Fires after drop. For valid drops, it exposes `context.async` which you can set to true to signal that additional
   * processing is needed before finalizing the drop (such as showing some dialog). When that operation is done, call
   * `context.finalize(true/false)` with a boolean that determines the outcome of the drop.
   *
   * You can signal that the drop is valid or invalid by setting `context.valid = false;`
   *
   * For translate type drags with {@link #config-cloneTarget}, you can also set `transitionTo` if you want to animate
   * the dragged proxy to a position before finalizing the operation. See class intro text for example usage.
   *
   * @event drop
   * @param {Core.helper.DragHelper} source
   * @param {Object} context
   * @param {HTMLElement} context.element The element which we are moving, could be a cloned version of grabbed, or the grabbed element itself
   * @param {HTMLElement} context.target The target element below the cursor
   * @param {HTMLElement} context.grabbed The original element upon which the mousedown event triggered a drag operation
   * @param {HTMLElement[]} context.relatedElements An array of extra elements dragged with the main dragged element
   * @param {Boolean} context.valid true if the drop position is valid
   */
  /**
   * Fires after {@link #event-drop} and after drag proxy has animated to its final position (if setting `transitionTo`
   * on the drag context object).
   * @private
   * @event dropFinalized
   * @param {Core.helper.DragHelper} source
   * @param {Object} context
   * @param {HTMLElement} context.element The element which we are moving, could be a cloned version of grabbed, or the grabbed element itself
   * @param {HTMLElement} context.target The target element below the cursor
   * @param {HTMLElement} context.grabbed The original element upon which the mousedown event triggered a drag operation
   */
  onPointerDown(event) {
    const me = this;
    if (
      // Left button or touch allowed
      event.button !== 0 || // If a drag is ongoing already, finalize it and don't proceed with new drag (happens if pointerup happened
      // when current window wasn't focused - tab switch or window switch). Also handles the edge case of trying to
      // start a new drag while previous is awaiting finalization, in which case it just bails out.
      me.context
    ) {
      return;
    }
    if (me.isElementDraggable && !me.isElementDraggable(event.target, event)) {
      return;
    }
    me.startEvent = event;
    const handled = me.isContainerDrag
      ? me.grabContainerDrag(event)
      : me.grabTranslateDrag(event);
    if (handled) {
      me.blurDetacher = EventHelper.on({
        element: globalThis,
        blur: me.onWindowBlur,
        thisObj: me,
      });
      const dragListeners = {
        element: me.mouseMoveListenerElement,
        thisObj: me,
        capture: true,
        keydown: rootElementListeners.keydown,
      };
      if (event.pointerType === "touch") {
        me.touchStartTimer = me.setTimeout(
          () => (me.touchStartTimer = null),
          me.touchStartDelay,
          "touchStartDelay",
        );
        dragListeners.touchmove = {
          handler: rootElementListeners.touchmove,
          passive: false,
          // We need to be able to preventDefault on the touchmove
        };
        dragListeners.touchend = dragListeners.pointerup =
          rootElementListeners.touchend;
      } else {
        dragListeners.pointermove = rootElementListeners.move;
        dragListeners.pointerup = rootElementListeners.up;
      }
      me.dragListenersDetacher = EventHelper.on(dragListeners);
      if (
        me.dragWithin &&
        me.dragWithin !== me.outerElement &&
        me.outerElement.contains(me.dragWithin)
      ) {
        const box = Rectangle.from(me.dragWithin, me.outerElement);
        me.minY = box.top;
        me.maxY = box.bottom;
        me.minX = box.left;
        me.maxX = box.right;
      }
    }
  }
  async internalMove(event) {
    var _a4, _b;
    if (event.scrollInitiated) {
      return;
    }
    const me = this,
      { context } = me,
      distance = EventHelper.getDistanceBetween(me.startEvent, event),
      abortTouchDrag = me.touchStartTimer && distance > me.dragThreshold;
    if (abortTouchDrag) {
      me.abort(true);
      return;
    }
    if (
      !me.touchStartTimer &&
      (context == null ? void 0 : context.element) &&
      (context.started || distance >= me.dragThreshold) && // Ignore text nodes
      ((_a4 = event.target) == null ? void 0 : _a4.nodeType) ===
        Node.ELEMENT_NODE
    ) {
      if (!context.started) {
        if (me.trigger("beforeDragStart", { context, event }) === false) {
          return me.abort();
        }
        if (me.isContainerDrag) {
          me.startContainerDrag(event);
        } else {
          me.startTranslateDrag(event);
        }
        context.started = true;
        (_b = me.scrollManager) == null
          ? void 0
          : _b.startMonitoring(
              ObjectHelper.merge(
                {
                  scrollables: [
                    {
                      element: me.dragWithin || me.outerElement,
                    },
                  ],
                  callback: me.onScrollManagerScrollCallback,
                },
                me.monitoringConfig,
              ),
            );
        context.outermostEl = DomHelper.getOutermostElement(event.target);
        context.outermostEl.classList.add("b-draghelper-active");
        if (me.dropTargetSelector && me.dropTargetCls) {
          DomHelper.getRootElement(me.outerElement)
            .querySelectorAll(me.dropTargetSelector)
            .forEach((el) => el.classList.add(me.dropTargetCls));
        }
        const result = me.trigger("dragStart", { context, event });
        if (ObjectHelper.isPromise(result)) {
          await result;
        }
        context.moveUnblocked = true;
        if (me.isContainerDrag) {
          me.onContainerDragStarted(event);
        } else {
          me.onTranslateDragStarted(event);
        }
        me.trigger("afterDragStart", { context, event });
      }
      if (context.moveUnblocked) {
        if (me._cachedMouseEvent) {
          me.update(event);
          me.update(me._cachedMouseEvent);
          delete me._cachedMouseEvent;
        } else {
          me.update(event);
        }
      } else {
        me._cachedMouseEvent = event;
      }
      if (event.type === "touchmove") {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }
  }
  onScrollManagerScrollCallback(config) {
    var _a4;
    const { lastMouseMoveEvent } = this;
    if (
      ((_a4 = this.context) == null ? void 0 : _a4.element) &&
      lastMouseMoveEvent
    ) {
      lastMouseMoveEvent.isScroll = true;
      this.update(lastMouseMoveEvent, config);
    }
  }
  onTouchMove(event) {
    this.internalMove(event);
  }
  /**
   * Move drag element with mouse.
   * @param event
   * @fires beforeDragStart
   * @fires dragStart
   * @private
   */
  onMouseMove(event) {
    this.internalMove(event);
  }
  /**
   * Updates drag, called when an element is grabbed and mouse moves
   * @private
   * @fires drag
   */
  update(event, scrollManagerConfig) {
    const me = this,
      { context } = me,
      scrollingPageElement = document.scrollingElement || document.body;
    let target = me.getMouseMoveEventTarget(event);
    if (event.type === "touchmove") {
      const touch = event.changedTouches[0];
      target = DomHelper.elementFromPoint(
        touch.clientX + scrollingPageElement.scrollLeft,
        touch.clientY + scrollingPageElement.scrollTop,
      );
    }
    context.target = target;
    let internallyValid =
      me.allowDropOutside ||
      !me.dragWithin ||
      me.dragWithin.contains(event.target);
    if (internallyValid && me.dropTargetSelector) {
      internallyValid =
        internallyValid &&
        Boolean(
          target == null ? void 0 : target.closest(me.dropTargetSelector),
        );
    }
    if (me.isContainerDrag) {
      me.updateContainerProxy(event, scrollManagerConfig);
    } else {
      me.updateTranslateProxy(event, scrollManagerConfig);
    }
    context.valid = internallyValid;
    me.trigger("drag", { context, event });
    if (me.isContainerDrag) {
      me.updateContainerDrag(event, scrollManagerConfig);
    }
    context.valid = context.valid && internallyValid;
    for (const element of me.draggedElements) {
      element.classList.toggle(me.invalidCls, !context.valid);
    }
    if (event) {
      me.lastMouseMoveEvent = event;
    }
  }
  get draggedElements() {
    var _a4;
    const { context } = this;
    return [
      context.dragProxy || context.element,
      ...((_a4 = context.relatedElements) != null ? _a4 : []),
    ];
  }
  /**
   * Abort dragging
   * @fires abort
   */
  async abort(silent = false) {
    var _a4, _b;
    const me = this,
      { context } = me;
    (_b = (_a4 = me.scrollManager) == null ? void 0 : _a4.stopMonitoring) ==
    null
      ? void 0
      : _b.call(_a4);
    me.removeListeners();
    if ((context == null ? void 0 : context.started) && !context.aborted) {
      context.element.getBoundingClientRect();
      context.valid = false;
      if (me.isContainerDrag) {
        me.abortContainerDrag(void 0, void 0, silent);
      } else {
        me.abortTranslateDrag(void 0, void 0, silent);
      }
      context.aborted = true;
    } else {
      me.reset(true);
    }
  }
  // Empty class implementation. If listeners *are* added, the detacher is added
  // as an instance property. So this is always callable.
  removeListeners() {
    var _a4, _b;
    (_a4 = this.dragListenersDetacher) == null ? void 0 : _a4.call(this);
    (_b = this.blurDetacher) == null ? void 0 : _b.call(this);
  }
  // Called when a drag operation is completed, or aborted
  // Removes DOM listeners and resets context
  reset(silent) {
    const me = this,
      { context } = me;
    if (context == null ? void 0 : context.started) {
      for (const element of me.draggedElements) {
        element.classList.remove(me.invalidCls);
      }
      context.outermostEl.classList.remove("b-draghelper-active");
      if (me.isContainerDrag) {
        context.dragProxy.remove();
      } else {
        me.cleanUp();
      }
      if (me.dropTargetSelector && me.dropTargetCls) {
        DomHelper.getRootElement(me.outerElement)
          .querySelectorAll(me.dropTargetSelector)
          .forEach((el) => el.classList.remove(me.dropTargetCls));
      }
    }
    me.removeListeners();
    if (!silent) {
      me.trigger("reset");
    }
    me.context = me.lastMouseMoveEvent = null;
  }
  onTouchEnd(event) {
    this.onMouseUp(event);
  }
  /**
   * This is a capture listener, only added during drag, which prevents a click gesture
   * propagating from the terminating mouseup gesture
   * @param {MouseEvent} event
   * @private
   */
  onDocumentClick(event) {
    event.stopPropagation();
  }
  /**
   * Drop on mouse up (if dropped on valid target).
   * @param event
   * @private
   */
  onMouseUp(event) {
    var _a4;
    const me = this,
      { context } = me;
    me.removeListeners();
    if (context) {
      (_a4 = me.scrollManager) == null ? void 0 : _a4.stopMonitoring();
      if (context.started) {
        if (context.moveUnblocked) {
          event.stopPropagation();
          context.finalizing = true;
          if (me.isContainerDrag) {
            me.finishContainerDrag(event);
          } else {
            me.finishTranslateDrag(event);
          }
          EventHelper.on({
            element: document,
            thisObj: me,
            click: rootElementListeners.docclick,
            capture: true,
            expires: me.clickSwallowDuration,
            // In case a click did not ensue, remove the listener
            once: true,
          });
        } else {
          me.ion({
            drag() {
              me.onMouseUp(event);
            },
            once: true,
          });
        }
      } else {
        me.reset(true);
      }
    }
  }
  /**
   * Cancel on ESC key
   * @param event
   * @private
   */
  onKeyDown(event) {
    var _a4;
    if (
      ((_a4 = this.context) == null ? void 0 : _a4.started) &&
      event.key === "Escape"
    ) {
      event.stopImmediatePropagation();
      this.abort();
    }
  }
  onWindowBlur() {
    if (this.context && !this.context.finalizing) {
      this.abort();
    }
  }
  /**
   * Creates the proxy element to be dragged, when using {@link #config-cloneTarget}. Clones the original element by default.
   * Override it to provide your own custom HTML element structure to be used as the drag proxy.
   * @param {HTMLElement} element The element from which the drag operation originated
   * @returns {HTMLElement}
   */
  createProxy(element) {
    if (this.proxySelector) {
      element = element.querySelector(this.proxySelector) || element;
    }
    const proxy = element.cloneNode(true);
    proxy.removeAttribute("id");
    return proxy;
  }
  //endregion
  get isContainerDrag() {
    return this.mode === "container";
  }
  /**
   * Animated the proxy element to be aligned with the passed element. Returns a Promise which resolves after the
   * DOM transition completes. Only applies to 'translateXY' mode.
   * @param {HTMLElement|Core.helper.util.Rectangle} element The target element or a Rectangle
   * @param {AlignSpec} [alignSpec] An object describing how to the align drag proxy to the target element
   * to offset the aligned widget further from the target. May be configured as -ve to move the aligned widget
   * towards the target - for example producing the effect of the anchor pointer piercing the target.
   */
  async animateProxyTo(targetElement, alignSpec = { align: "c-c" }) {
    const { context, draggedElements } = this,
      { element } = context,
      targetRect = targetElement.isRectangle
        ? targetElement
        : Rectangle.from(targetElement);
    draggedElements.forEach((el) => {
      el.classList.add("b-drag-final-transition");
      DomHelper.alignTo(el, targetRect, alignSpec);
    });
    await EventHelper.waitForTransitionEnd({
      element,
      property: "all",
      thisObj: this,
      once: true,
    });
    draggedElements.forEach((el) =>
      el.classList.remove("b-drag-final-transition"),
    );
  }
  /**
   * Returns true if a drag operation is active
   * @property {Boolean}
   * @readonly
   */
  get isDragging() {
    var _a4;
    return Boolean((_a4 = this.context) == null ? void 0 : _a4.started);
  }
  //#region Salesforce hooks
  getMouseMoveEventTarget(event) {
    return !event.isScroll
      ? event.target
      : DomHelper.elementFromPoint(event.clientX, event.clientY);
  }
  //#endregion
};
DragHelper._$name = "DragHelper";

// ../Core/lib/Core/helper/ResizeHelper.js
var documentListeners = {
  down: "onMouseDown",
  move: "onMouseMove",
  up: "onMouseUp",
  docclick: "onDocumentClick",
  touchstart: {
    handler: "onTouchStart",
    // We preventDefault touchstart so as not to scroll. Must not be passive.
    // https://developers.google.com/web/updates/2017/01/scrolling-intervention
    passive: false,
  },
  touchmove: "onTouchMove",
  touchend: "onTouchEnd",
  keydown: "onKeyDown",
};
var ResizeHelper = class extends Events_default(Base) {
  //region Config
  static get defaultConfig() {
    return {
      /**
       * CSS class added when resizing
       * @config {String}
       * @default
