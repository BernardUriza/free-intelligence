var whitespace = /\s+/;
var createClsProps = (result, cls2) => {
  result[cls2] = 1;
  return result;
};
var Config = class _Config {
  /**
   * Returns the `Config` instance for the given `name` and `options`.
   * @param {String} name The name of the config (e.g., 'text' for the text config).
   * @param {Object} [options] Config behavior options.
   * @returns {Core.Config}
   * @internal
   */
  static get(name, options) {
    const { cache } = this,
      baseCfg = cache[name] || (cache[name] = new _Config(name));
    let cfg = baseCfg,
      key;
    if (options) {
      key = _Config.makeCacheKey(name, options);
      if (!(cfg = key && cache[key])) {
        cfg = baseCfg.extend(options);
        if (key) {
          cache[key] = cfg;
        }
      }
    }
    return cfg;
  }
  constructor(name) {
    const me = this,
      cap = name[0].toUpperCase() + name.substr(1);
    me.base = me;
    me.name = name;
    me.field = "_" + name;
    me.capName = cap;
    me.changer = "change" + cap;
    me.initializing = "initializing" + cap;
    me.updater = "update" + cap;
  }
  /**
   * The descriptor to use with `Reflect.defineProperty()` for defining this config's getter and setter.
   * @property {Object}
   * @private
   */
  get descriptor() {
    let descriptor = this._descriptor;
    if (!descriptor || !hasOwnProperty3.call(this, "_descriptor")) {
      this._descriptor = descriptor = this.makeDescriptor();
    }
    return descriptor;
  }
  /**
   * The descriptor to use with `Reflect.defineProperty()` for defining this config's initter.
   * @property {Object}
   * @private
   */
  get initDescriptor() {
    let descriptor = this._initDescriptor;
    if (!descriptor || !hasOwnProperty3.call(this, "_initDescriptor")) {
      this._initDescriptor = descriptor = this.makeInitter();
    }
    return descriptor;
  }
  /**
   * This method compares two values for semantic equality. By default, this is based on the `===` operator. This
   * is often overridden for configs that accept `Date` or array values.
   * @param {*} value1
   * @param {*} value2
   * @returns {Boolean}
   * @internal
   */
  equal(value1, value2) {
    return value1 === value2;
  }
  /**
   * Extends this config with a given additional set of options. These objects are just prototype extensions of this
   * instance.
   * @param {Object} options
   * @returns {Core.Config}
   * @internal
   */
  extend(options) {
    const cfg = Object.assign(Object.create(this), options),
      { equal: equal2, merge } = options,
      { equalityMethods } = _Config;
    if (typeof equal2 === "string") {
      if (equal2.endsWith("[]")) {
        cfg.equal = _Config.makeArrayEquals(
          equalityMethods[equal2.substr(0, equal2.length - 2)],
        );
      } else {
        cfg.equal = equalityMethods[equal2];
      }
    }
    if (typeof merge === "string") {
      cfg.merge = _Config.mergeMethods[merge];
    }
    return cfg;
  }
  /**
   * Defines the property on a given target object via `Reflect.defineProperty()`. If the object has its own getter,
   * it will be preserved. It is invalid to define a setter.
   * @param {Object} target
   * @internal
   */
  define(target) {
    const existing = getOwnPropertyDescriptor(target, this.name);
    let descriptor = this.descriptor;
    if (existing && existing.get) {
      descriptor = Object.assign({}, descriptor);
      descriptor.get = existing.get;
    }
    defineProperty(target, this.name, descriptor);
  }
  /**
   * Defines the property initter on the `target`. This is a property getter/setter that propagates the configured
   * value when the property is read.
   * @param {Object} target
   * @param {*} value
   * @internal
   */
  defineInitter(target, value) {
    const { name } = this,
      properties = target[instancePropertiesSymbol];
    let lazyValues, prop;
    if (
      !properties[name] /* assign */ &&
      (prop = getOwnPropertyDescriptor(target, name)) &&
      !("value" in prop)
    ) {
      properties[name] = prop;
    }
    defineProperty(target, name, this.initDescriptor);
    if (this.lazy) {
      lazyValues =
        target[lazyConfigValues] ||
        (target[lazyConfigValues] = /* @__PURE__ */ new Map());
      lazyValues.set(name, value);
    }
  }
  /**
   * Returns an equality function for arrays of a base type, for example `'date'`.
   * @param {Function} [fn] The function to use to compare array elements. By default, operator `===` is used.
   * @returns {Function}
   * @private
   */
  static makeArrayEquals(fn2) {
    return (value1, value2) => {
      let i,
        equal2 = value1 && value2 && value1.length === (i = value2.length);
      if (equal2 && Array.isArray(value1) && Array.isArray(value2)) {
        if (fn2) {
          while (equal2 && i-- > 0) {
            equal2 = fn2(value1[i], value2[i]);
          }
        } else {
          while (equal2 && i-- > 0) {
            equal2 = value1[i] === value2[i];
          }
        }
      } else {
        equal2 = fn2 ? fn2(value1, value2) : value1 === value2;
      }
      return equal2;
    };
  }
  /**
   * Returns the key to use in the Config `cache`.
   * @param {String} name The name of the config property.
   * @param {Object} options The config property options.
   * @returns {String}
   * @private
   */
  static makeCacheKey(name, options) {
    const keys = Object.keys(options).sort();
    for (let key, type, value, i = keys.length; i-- > 0; ) {
      value = options[(key = keys[i])];
      if (value == null && value === false) {
        keys.splice(i, 1);
      } else {
        type = typeof value;
        if (type === "function") {
          return null;
        }
        if (type === "string") {
          keys[i] = `${key}:"${value}"`;
        } else if (type === "number") {
          keys[i] = `${key}:${value}`;
        }
      }
    }
    return keys.length ? `${name}>${keys.join("|")}` : name;
  }
  /**
   * Creates and returns a property descriptor for this config suitable to be passed to `Reflect.defineProperty()`.
   * @returns {Object}
   * @private
   */
  makeDescriptor() {
    const config = this,
      { base, field: field2, changer, updater, name } = config;
    if (base !== config && base.equal === config.equal) {
      return base.descriptor;
    }
    return {
      get() {
        var _a4;
        (_a4 = this.configObserver) == null ? void 0 : _a4.get(name, this);
        return this[field2];
      },
      set(value) {
        var _a4, _b;
        const me = this;
        let was = me[field2],
          applied,
          newValue;
        if (typeof value === "string") {
          let resolvedValue = value;
          if (value.startsWith("up.")) {
            resolvedValue =
              (_a4 = me.owner) == null
                ? void 0
                : _a4.resolveProperty(value.slice(3));
          } else if (value.startsWith("this.")) {
            resolvedValue = me.resolveProperty(value.slice(5));
          }
          if (resolvedValue !== void 0 && typeof resolvedValue !== "function") {
            value = resolvedValue;
          }
        }
        if (me[changer]) {
          applied = (newValue = me[changer](value, was)) === void 0;
          if (!applied) {
            value = newValue;
            was = me[field2];
          }
        }
        if (
          !applied &&
          !(config.equal === equal ? was === value : config.equal(was, value))
        ) {
          me[field2] = value;
          applied = true;
          (_b = me[updater]) == null ? void 0 : _b.call(me, value, was);
        }
        if (applied && !me.isDestroyed && !me.onConfigChange.$nullFn) {
          me.onConfigChange({ name, value, was, config });
        }
      },
    };
  }
  /**
   * Creates and returns a property descriptor for this config's initter suitable to pass to
   * `Reflect.defineProperty()`.
   * @returns {Object}
   * @private
   */
  makeInitter() {
    const config = this;
    if (config !== config.base) {
      if (config.lazy) {
        return config.makeLazyInitter();
      }
      return config.base.initDescriptor;
    }
    return config.makeBasicInitter();
  }
  makeBasicInitter() {
    const config = this,
      { initializing, name } = config;
    return {
      configurable: true,
      get() {
        const me = this;
        config.removeInitter(me);
        me[initializing] = true;
        me[name] = me[configuringSymbol][name];
        me[initializing] = false;
        me.configDone[name] = true;
        return me[name];
      },
      set(value) {
        config.removeInitter(this);
        this.configDone[name] = true;
        this[name] = value;
      },
    };
  }
  makeLazyInitter() {
    const config = this,
      { initializing, name } = config;
    return {
      configurable: true,
      get() {
        const me = this,
          value = me[lazyConfigValues].get(name);
        config.removeInitter(me);
        if (!me.isDestroying) {
          me[initializing] = true;
          me[name] = value;
          me[initializing] = false;
        }
        return me[name];
      },
      set(value) {
        config.removeInitter(this);
        this[name] = value;
      },
    };
  }
  /**
   * Removes the property initter and restores the instance to its original form.
   * @param {Object} instance
   * @private
   */
  removeInitter(instance) {
    const { name } = this,
      instanceProperty = instance[instancePropertiesSymbol][name],
      lazyValues = instance[lazyConfigValues];
    if (instanceProperty) {
      defineProperty(instance, name, instanceProperty);
    } else {
      delete instance[name];
    }
    if (
      (lazyValues == null ? void 0 : lazyValues.delete(name)) &&
      !lazyValues.size
    ) {
      delete instance[lazyConfigValues];
    }
  }
  setDefault(cls2, value) {
    defineProperty(cls2.prototype, this.field, {
      configurable: true,
      writable: true,
      // or else "this._value = x" will fail
      value,
    });
  }
  /**
   * This method combines (merges) two config values. This is called in two cases:
   *
   *  - When a derived class specifies the value of a config defined in a super class.
   *  - When a value is specified in the instance config object.
   *
   * @param {*} newValue In the case of derived classes, this is the config value of the derived class. In the case
   * of the instance config, this is the instance config value.
   * @param {*} currentValue In the case of derived classes, this is the config value of the super class. In the case
   * of the instance config, this is the class config value.
   * @param {Object} metaNew The class meta object from which the `newValue` is coming. This parameter is `null` if
   * the `newValue` is from an instance configuration.
   * @param {Object} metaCurrent The class meta object from which the `currentValue` is coming. This parameter is
   * `null` if the `currentValue` is not from a class configuration.
   * @returns {*}
   * @internal
   */
  merge(newValue, currentValue) {
    if (currentValue && newValue && Objects.isObject(newValue)) {
      if (currentValue.isBase) {
        return currentValue.setConfig(newValue);
      }
      if (Objects.isObject(currentValue)) {
        newValue = Objects.merge(Objects.clone(currentValue), newValue);
      }
    }
    return newValue;
  }
};
var { prototype } = Config;