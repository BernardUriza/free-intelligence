      }
      case "quarter":
        DateHelper.startOf(dt, "month", false);
        return DateHelper.add(dt, 3 - (dt.getMonth() % 3), "month", false);
      default: {
        const duration = DateHelper.as(
            resolutionUnit,
            DateHelper.diff(relativeTo, dt),
          ),
          offset =
            resolutionUnit === "year"
              ? 0
              : DateHelper.as(
                  resolutionUnit,
                  relativeTo.getTimezoneOffset() - dt.getTimezoneOffset(),
                  "minute",
                ),
          snappedDuration =
            Math.round((duration + offset) / increment) * increment;
        return DateHelper.add(
          relativeTo,
          snappedDuration - offset,
          resolutionUnit,
          false,
        );
      }
    }
  }
  // private
  ceilDate(date, relativeToStart, resolutionUnit, increment) {
    const me = this;
    relativeToStart = relativeToStart !== false;
    increment = increment || (relativeToStart ? me.resolutionIncrement : 1);
    const unit =
        resolutionUnit || (relativeToStart ? me.resolutionUnit : me.mainUnit),
      dt = DateHelper.clone(date);
    let doCall = false;
    switch (unit) {
      case "minute":
        doCall = !DateHelper.isStartOf(dt, "minute");
        break;
      case "hour":
        doCall = !DateHelper.isStartOf(dt, "hour");
        break;
      case "day":
      case "date":
        doCall = !DateHelper.isStartOf(dt, "day");
        break;
      case "week":
        DateHelper.startOf(dt, "day", false);
        doCall =
          dt.getDay() !== me.weekStartDay || !DateHelper.isEqual(dt, date);
        break;
      case "month":
        DateHelper.startOf(dt, "day", false);
        doCall = dt.getDate() !== 1 || !DateHelper.isEqual(dt, date);
        break;
      case "quarter":
        DateHelper.startOf(dt, "day", false);
        doCall =
          dt.getMonth() % 3 !== 0 ||
          dt.getDate() !== 1 ||
          !DateHelper.isEqual(dt, date);
        break;
      case "year":
        DateHelper.startOf(dt, "day", false);
        doCall =
          dt.getMonth() !== 0 ||
          dt.getDate() !== 1 ||
          !DateHelper.isEqual(dt, date);
        break;
    }
    if (doCall) {
      return DateHelper.getNext(dt, unit, increment, me.weekStartDay);
    }
    return dt;
  }
  //endregion
  //region Ticks
  get include() {
    return this._include;
  }
  set include(include) {
    const me = this;
    me._include = include;
    me.continuous = !include;
    if (!me.isConfiguring) {
      me.startDate = me._configuredStartDate;
      me.endDate = me._configuredEndDate;
      me.internalOnReconfigure();
      me.trigger("includeChange");
    }
  }
  // Check if a certain date is included based on timeAxis.include rules
  processExclusion(startDate, endDate, unit) {
    const { include } = this;
    if (include) {
      return Object.entries(include).some(([includeUnit, rule]) => {
        if (!rule) {
          return false;
        }
        const { from, to } = rule;
        if (
          DateHelper.compareUnits("day", unit) >= 0 &&
          DateHelper.getLargerUnit(includeUnit) === unit
        ) {
          if (from) {
            DateHelper.set(startDate, includeUnit, from);
          }
          if (to) {
            let stepUnit = unit;
            if (unit === "day") {
              stepUnit = "date";
            }
            DateHelper.set(endDate, {
              [stepUnit]: DateHelper.get(endDate, stepUnit) - 1,
              [includeUnit]: to,
            });
          }
        }
        if (DateHelper.compareUnits(includeUnit, unit) >= 0) {
          const datePart =
            includeUnit === "day"
              ? startDate.getDay()
              : DateHelper.get(startDate, includeUnit);
          if ((from && datePart < from) || (to && datePart >= to)) {
            return true;
          }
        }
      });
    }
    return false;
  }
  // Calculate constants used for exclusion when scaling within larger ticks
  initExclusion() {
    Object.entries(this.include).forEach(([unit, rule]) => {
      if (rule) {
        const { from, to } = rule;
        rule.lengthFactor =
          DateHelper.getUnitToBaseUnitRatio(
            unit,
            DateHelper.getLargerUnit(unit),
          ) /
          (to - from);
        rule.lengthFactorExcl =
          DateHelper.getUnitToBaseUnitRatio(
            unit,
            DateHelper.getLargerUnit(unit),
          ) /
          (to - from - 1);
        rule.center = from + from / (rule.lengthFactor - 1);
      }
    });
  }
  /**
   * Method generating the ticks for this time axis. Should return an array of ticks . Each tick is an object of the following structure:
   * ```
   * {
   *    startDate : ..., // start date
   *    endDate   : ...  // end date
   * }
   * ```
   * Take notice, that this function either has to be called with `start`/`end` parameters, or create those variables.
   *
   * To see it in action please check out our [TimeAxis](https://bryntum.com/products/scheduler/examples/timeaxis/) example and navigate to "Compressed non-working time" tab.
   *
   * @member {Function} generateTicks
   * @param {Date} axisStartDate The start date of the interval
   * @param {Date} axisEndDate The end date of the interval
   * @param {DurationUnit} unit The unit of the time axis
   * @param {Number} increment The increment for the unit specified.
   * @returns {Array|undefined} ticks The ticks representing the time axis, or no return value to use the default tick generation
   */
  updateGenerateTicks() {
    if (!this.isConfiguring) {
      this.reconfigure(this);
    }
  }
  _generateTicks(
    axisStartDate,
    axisEndDate,
    unit = this.unit,
    increment = this.increment,
  ) {
    const me = this,
      ticks = [],
      usesExclusion = Boolean(me.include);
    let intervalEnd,
      tickEnd,
      isExcluded,
      dstDiff = 0,
      { startDate, endDate } = me.getAdjustedDates(axisStartDate, axisEndDate),
      tryRelyingOnExclusion = false;
    me.tickCache = {};
    if (usesExclusion) {
      me.initExclusion();
    }
    while (startDate < endDate) {
      intervalEnd = DateHelper.getNext(
        startDate,
        unit,
        increment,
        me.weekStartDay,
      );
      if (!me.autoAdjust && intervalEnd > endDate && !tryRelyingOnExclusion) {
        intervalEnd = new Date(endDate.getTime());
      }
      if (
        unit === "hour" &&
        increment > 1 &&
        ticks.length > 0 &&
        dstDiff === 0
      ) {
        const prev = ticks[ticks.length - 1];
        dstDiff =
          ((prev.startDate.getHours() + increment) % 24) -
          prev.endDate.getHours();
        if (dstDiff !== 0) {
          intervalEnd = DateHelper.add(intervalEnd, dstDiff, "hour");
        }
      }
      isExcluded = false;
      if (usesExclusion) {
        tickEnd = new Date(intervalEnd.getTime());
        isExcluded = me.processExclusion(startDate, intervalEnd, unit);
        if (tryRelyingOnExclusion) {
          if (!me.autoAdjust && intervalEnd > endDate) {
            startDate = tickEnd;
            continue;
          }
        } else if (intervalEnd < startDate) {
          tryRelyingOnExclusion = true;
          continue;
        }
      } else {
        tickEnd = intervalEnd;
      }
      if (!isExcluded) {
        ticks.push({
          id: ticks.length + 1,
          startDate,
          endDate: intervalEnd,
        });
        me.tickCache[startDate.getTime()] = ticks.length - 1;
      }
      startDate = tickEnd;
    }
    return ticks;
  }
  /**
   * How many ticks are visible across the TimeAxis.
   *
   * Usually, this is an integer because {@link #config-autoAdjust} means that the start and end
   * dates are adjusted to be on tick boundaries.
   * @property {Number}
   * @internal
   */
  get visibleTickTimeSpan() {
    const me = this;
    return me.isContinuous ? me.visibleTickEnd - me.visibleTickStart : me.count;
  }
  /**
   * Gets a tick "coordinate" representing the date position on the time scale. Returns -1 if the date is not part of the time axis.
   * @param {Date} date the date
   * @returns {Number} the tick position on the scale or -1 if the date is not part of the time axis
   */
  getTickFromDate(date) {
    var _a4, _b;
    const me = this,
      ticks = me.records,
      dateMS =
        (_b = (_a4 = date.getTime) == null ? void 0 : _a4.call(date)) != null
          ? _b
          : date;
    let begin = 0,
      end = ticks.length - 1,
      middle,
      tick,
      tickStart,
      tickEnd;
    if (
      !ticks.length ||
      dateMS < ticks[0].startDateMS ||
      dateMS > ticks[end].endDateMS
    ) {
      return -1;
    }
    if (me.isContinuous) {
      while (begin < end) {
        middle = (begin + end + 1) >> 1;
        if (dateMS > ticks[middle].endDateMS) {
          begin = middle + 1;
        } else if (dateMS < ticks[middle].startDateMS) {
          end = middle - 1;
        } else {
          begin = middle;
        }
      }
      tick = ticks[begin];
      tickStart = tick.startDateMS;
      if (dateMS > tickStart) {
        tickEnd = tick.endDateMS;
        begin += (dateMS - tickStart) / (tickEnd - tickStart);
      }
      return Math.min(Math.max(begin, me.visibleTickStart), me.visibleTickEnd);
    } else {
      for (let i = 0; i <= end; i++) {
        tickEnd = ticks[i].endDateMS;
        if (dateMS <= tickEnd) {
          tickStart = ticks[i].startDateMS;
          tick =
            i +
            (dateMS > tickStart
              ? (dateMS - tickStart) / (tickEnd - tickStart)
              : 0);
          return tick;
        }
      }
    }
  }
  getSnappedTickFromDate(date) {
    const startTickIdx = Math.floor(this.getTickFromDate(date));
    return this.getAt(startTickIdx);
  }
  /**
   * Gets the time represented by a tick "coordinate".
   * @param {Number} tick the tick "coordinate"
   * @param {'floor'|'round'|'ceil'} [roundingMethod] Rounding method to use. 'floor' to take the tick (lowest header
   * in a time axis) start date, 'round' to round the value to nearest increment or 'ceil' to take the tick end date
   * @returns {Date} The date to represented by the tick "coordinate", or null if invalid.
   */
  getDateFromTick(tick, roundingMethod) {
    const me = this;
    if (tick === me.visibleTickEnd) {
      return me.endDate;
    }
    const wholeTick = Math.floor(tick),
      fraction = tick - wholeTick,
      t = me.getAt(wholeTick);
    if (!t) {
      return null;
    }
    const start =
        wholeTick === 0 && me.isContinuous ? me.adjustedStart : t.startDate,
      end =
        wholeTick === me.count - 1 && me.isContinuous
          ? me.adjustedEnd
          : t.endDate;
    let date = DateHelper.add(start, fraction * (end - start), "millisecond");
    if (roundingMethod) {
      date = me[roundingMethod + "Date"](date);
    }
    return date;
  }
  /**
   * Returns the ticks of the timeaxis in an array of objects with a "startDate" and "endDate".
   * @property {Scheduler.model.TimeSpan[]}
   */
  get ticks() {
    return this.records;
  }
  /**
   * Caches ticks and start/end dates for faster processing during rendering of events.
   * @private
   */
  updateTickCache(onlyStartEnd = false) {
    const me = this;
    if (me.count) {
      me._start = me.first.startDate;
      me._end = me.last.endDate;
      me._startMS = me.startDate.getTime();
      me._endMS = me.endDate.getTime();
    } else {
      me._start = me._end = me._startMs = me._endMS = null;
    }
    if (!onlyStartEnd) {
      me.tickCache = {};
      me.forEach((tick, i) => (me.tickCache[tick.startDate.getTime()] = i));
    }
  }
  //endregion
  //region Axis
  /**
   * Returns true if the passed date is inside the span of the current time axis.
   * @param {Date} date The date to query for
   * @returns {Boolean} true if the date is part of the time axis
   */
  dateInAxis(date, inclusiveEnd = false) {
    const me = this,
      axisStart = me.startDate,
      axisEnd = me.endDate;
    if (me.isContinuous) {
      return inclusiveEnd
        ? DateHelper.betweenLesserEqual(date, axisStart, axisEnd)
        : DateHelper.betweenLesser(date, axisStart, axisEnd);
    } else {
      const length = me.getCount();
      let tickStart, tickEnd, tick;
      for (let i = 0; i < length; i++) {
        tick = me.getAt(i);
        tickStart = tick.startDate;
        tickEnd = tick.endDate;
        if (
          (inclusiveEnd && date <= tickEnd) ||
          (!inclusiveEnd && date < tickEnd)
        ) {
          return date >= tickStart;
        }
      }
    }
    return false;
  }
  /**
   * Returns true if the passed timespan is part of the current time axis (in whole or partially).
   * @param {Date} start The start date
   * @param {Date} end The end date
   * @returns {Boolean} true if the timespan is part of the timeaxis
   */
  timeSpanInAxis(start, end) {
    const me = this;
    if (!end || end.getTime() === start.getTime()) {
      return this.dateInAxis(start, true);
    }
    if (me.isContinuous) {
      return DateHelper.intersectSpans(start, end, me.startDate, me.endDate);
    }
    return (
      (start < me.startDate && end > me.endDate) ||
      me.getTickFromDate(start) !== me.getTickFromDate(end)
    );
  }
  // Accepts a TimeSpan model (uses its cached MS values to be a bit faster during rendering)
  isTimeSpanInAxis(timeSpan) {
    var _a4;
    const me = this,
      { startMS, endMS } = me,
      { startDateMS } = timeSpan,
      endDateMS =
        (_a4 = timeSpan.endDateMS) != null ? _a4 : timeSpan.meta.endDateCached;
    if (!startDateMS || !endDateMS) {
      return false;
    }
    if (endDateMS === startDateMS) {
      return me.dateInAxis(timeSpan.startDate, true);
    }
    if (me.isContinuous) {
      return endDateMS > startMS && startDateMS < endMS;
    }
    const startTick = me.getTickFromDate(startDateMS),
      endTick = me.getTickFromDate(endDateMS);
    if (
      (startTick === me.count &&
        DateHelper.isEqual(timeSpan.startDate, me.last.endDate)) ||
      (endTick === 0 &&
        DateHelper.isEqual(timeSpan.endDate, me.first.startDate))
    ) {
      return false;
    }
    return (
      // Spanning entire axis
      (startDateMS < startMS && endDateMS > endMS) || // Unintentionally 0 wide (ticks excluded or outside)
      startTick !== endTick
    );
  }
  //endregion
  //region Iteration
  /**
   * Calls the supplied iterator function once per interval. The function will be called with four parameters, startDate endDate, index, isLastIteration.
   * @internal
   * @param {DurationUnit} unit The unit to use when iterating over the timespan
   * @param {Number} increment The increment to use when iterating over the timespan
   * @param {Function} iteratorFn The function to call
   * @param {Object} [thisObj] `this` reference for the function
   */
  forEachAuxInterval(unit, increment = 1, iteratorFn, thisObj = this) {
    const end = this.endDate;
    let dt = this.startDate,
      i = 0,
      intervalEnd;
    if (dt > end) throw new Error("Invalid time axis configuration");
    while (dt < end) {
      intervalEnd = DateHelper.min(
        DateHelper.getNext(dt, unit, increment, this.weekStartDay),
        end,
      );
      iteratorFn.call(thisObj, dt, intervalEnd, i, intervalEnd >= end);
      dt = intervalEnd;
      i++;
    }
  }
  //endregion
};
TimeAxis._$name = "TimeAxis";

// ../Scheduler/lib/Scheduler/view/model/TimeAxisViewModel.js
var TimeAxisViewModel = class extends Events_default() {
  //region Default config
  static get defaultConfig() {
    return {
      /**
       * The time axis providing the underlying data to be visualized
