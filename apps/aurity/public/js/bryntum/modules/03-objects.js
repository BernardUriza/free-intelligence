var afterRe = /\s*<\s*/;
var beforeRe = /\s*>\s*/;
var blendOptions = {};
var typeCache = {};
var emptyObject = Object.freeze({});
var Objects = class _Objects {
  static assign(dest, ...sources) {
    for (let source, key, i = 0; i < sources.length; i++) {
      source = sources[i];
      if (source) {
        for (key in source) {
          dest[key] = source[key];
        }
      }
    }
    return dest;
  }
  static assignIf(dest, ...sources) {
    for (let source, key, i = 0; i < sources.length; i++) {
      source = sources[i];
      if (source) {
        for (key in source) {
          if (!(key in dest) || dest[key] === void 0) {
            dest[key] = source[key];
          }
        }
      }
    }
    return dest;
  }
  static blend(dest, source, options) {
    options = options || blendOptions;
    dest = dest || {};
    const { clone = _Objects.clone, merge = _Objects.blend } = options;
    if (Array.isArray(source)) {
      if (source.length > 1) {
        source.forEach((s) => {
          dest = _Objects.blend(dest, s, options);
        });
        return dest;
      }
      source = source[0];
    }
    if (source) {
      let destValue, key, value;
      for (key in source) {
        value = source[key];
        if (value && _Objects.isObject(value)) {
          destValue = dest[key];
          options.key = key;
          if (destValue && _Objects.isObject(destValue)) {
            if (isFrozen(destValue)) {
              dest[key] = destValue = clone(destValue, options);
            }
            value = merge(destValue, value, options);
          } else {
            value = isFrozen(value) ? value : clone(value, options);
          }
        }
        dest[key] = value;
      }
    }
    return dest;
  }
  static clone(value, handler) {
    let cloned = value,
      key;
    if (value && typeof value === "object") {
      const options = handler && typeof handler === "object" && handler;
      if (options) {
        handler = null;
      }
      if (_Objects.isObject(value)) {
        if (value.skipClone) {
          cloned = value;
        } else {
          cloned = {};
          for (key in value) {
            cloned[key] = _Objects.clone(value[key]);
          }
        }
      } else if (Array.isArray(value)) {
        cloned = [];
        for (key = value.length; key-- > 0; ) {
          cloned[key] = _Objects.clone(value[key]);
        }
      } else if (_Objects.isDate(value)) {
        cloned = new Date(value.getTime());
      } else if (handler) {
        cloned = handler(value);
      }
    }
    return cloned;
  }
  static createTruthyKeys(source) {
    const keys = StringHelper.split(source),
      result = keys && {};
    if (keys) {
      for (const key of keys) {
        if (key) {
          result[key] = true;
        }
      }
    }
    return result;
  }
  /**
   * Returns value for a given path in the object
   * @param {Object} object Object to check path on
   * @param {String} path Dot-separated path, e.g. 'object.childObject.someKey'
   * @returns {*} Value associated with passed key
   */
  static getPath(object, path) {
    return path.split(".").reduce((result, key) => {
      return (result || emptyObject)[key];
    }, object);
  }
  /**
   * Returns value for a given path in the object, placing a passed default value in at the
   * leaf property and filling in undefined properties all the way down.
   * @param {Object} object Object to get path value for.
   * @param {String|Number|String[]|Number[]} path Dot-separated path, e.g. 'firstChild.childObject.someKey',
   * or the key path as an array, e.g. ['firstChild', 'childObject', 'someKey'].
   * @param {*} [defaultValue] Optionally the value to put in as the `someKey` property.
   * @returns {*} Value at the leaf position of the path.
   */
  static getPathDefault(object, path, defaultValue2) {
    const keys = Array.isArray(path)
        ? path
        : typeof path === "string"
          ? path.split(".")
          : [path],
      length = keys.length - 1;
    return keys.reduce((result, key, index) => {
      if (defaultValue2 && !(key in result)) {
        result[key] = index === length ? defaultValue2 : {};
      }
      return (result || emptyObject)[key];
    }, object);
  }
  /**
   * Finds a property descriptor for the passed object from all inheritance levels.
   * @param {Object} object The Object whose property to find.
   * @param {String} propertyName The name of the property to find.
   * @returns {Object} An ECMA property descriptor is the property was found, otherwise `null`
   */
  static getPropertyDescriptor(object, propertyName) {
    let result = null;
    for (
      let o = object;
      o && !result && !_Objects.hasOwn(o, "isBase");
      o = Object.getPrototypeOf(o)
    ) {
      result = Object.getOwnPropertyDescriptor(o, propertyName);
    }
    return result;
  }
  /**
   * Determines if the specified path exists
   * @param {Object} object Object to check path on
   * @param {String} path Dot-separated path, e.g. 'object.childObject.someKey'
   * @returns {Boolean}
   */
  static hasPath(object, path) {
    return path.split(".").every((key) => {
      if (object && key in object) {
        object = object[key];
        return true;
      }
      return false;
    });
  }
  static getTruthyKeys(source) {
    const keys = [];
    for (const key in source) {
      if (source[key]) {
        keys.push(key);
      }
    }
    return keys;
  }
  static getTruthyValues(source) {
    const values = [];
    for (const key in source) {
      if (source[key]) {
        values.push(source[key]);
      }
    }
    return values;
  }
  static isClass(object) {
    var _a4;
    if (
      typeof object === "function" &&
      ((_a4 = object.prototype) == null ? void 0 : _a4.constructor) === object
    ) {
      return true;
    }
    return false;
  }
  static isDate(object) {
    return (
      Boolean(object == null ? void 0 : object.getUTCDate) &&
      _Objects.typeOf(object) === "date"
    );
  }
  /**
   * Check if passed object is a Promise or contains `then` method.
   * Used to fix problems with detecting promises in code with `instance of Promise` when
   * Promise class is replaced with any other implementation like `ZoneAwarePromise` in Angular.
   * Related to these issues:
   * https://github.com/bryntum/support/issues/791
   * https://github.com/bryntum/support/issues/2990
   *
   * @param {Object} object object to check
   * @returns {Boolean} truthy value if object is a Promise
   * @internal
   */
  static isPromise(object) {
    if (Promise && Promise.resolve) {
      return (
        Promise.resolve(object) === object ||
        typeof (object == null ? void 0 : object.then) === "function"
      );
    }
    throw new Error("Promise not supported in your environment");
  }
  static isEmpty(object) {
    if (object && typeof object === "object") {
      for (const p in object) {
        return false;
      }
    }
    return true;
  }
  static isObject(value) {
    const C = value == null ? void 0 : value.constructor;
    return Boolean(
      C
        ? // An in-frame instance of Object
          C === Object || // Detect cross-frame objects, but exclude instance of custom classes named Object. typeOf(value) is
            // "object" even for instances of a class and typeOf(C) is "function" for all constructors. We'll have
            // to settle for relying on the fact that getPrototypeOf(Object.prototype) === null.
            // NOTE: this issue does come up in Scheduler unit tests at least.
            (C.getPrototypeOf &&
              C.prototype &&
              !Object.getPrototypeOf(C.prototype))
        : value && typeof value === "object",
    );
  }
  static isInstantiated(object) {
    return object
      ? typeof object === "object" && !_Objects.isObject(object)
      : false;
  }
  static merge(dest, ...sources) {
    return _Objects.blend(dest, sources);
  }
  /**
   * Merges two "items" objects. An items object is a simple object whose keys act as identifiers and whose values
   * are "item" objects. An item can be any object type. This method is used to merge such objects while maintaining
   * their property order. Special key syntax is used to allow a source object to insert a key before or after a key
   * in the `dest` object.
   *
   * For example:
   * ```javascript
   *  let dest = {
   *      foo : {},
   *      bar : {},
   *      fiz : {}
   *  }
   *
   *  console.log(Object.keys(dest));
   *  > ["foo", "bar", "fiz"]
   *
   *  dest = mergeItems(dest, {
   *      'zip > bar' : {}    // insert "zip" before "bar"
   *      'bar < zap' : {}    // insert "zap" after "bar"
   *  });
   *
   *  console.log(Object.keys(dest));
   *  > ["foo", "zip", "bar", "zap", "fiz"]
   * ```
   *
   * @param {Object} dest The destination object.
   * @param {Object|Object[]} src The source object or array of source objects to merge into `dest`.
   * @param {Object} [options] The function to use to merge items.
   * @param {Function} [options.merge] The function to use to merge items.
   * @returns {Object} The merged object. This will be the `dest` object.
   * @internal
   */
  static mergeItems(dest, src, options) {
    options = options || blendOptions;
    let anchor, delta, index, indexMap, key, shuffle, srcVal;
    const { merge = _Objects.blend } = options;
    dest = dest || {};
    if (Array.isArray(src)) {
      src.forEach((s) => {
        dest = _Objects.mergeItems(dest, s, options);
      });
    } else if (src) {
      for (key in src) {
        srcVal = src[key];
        anchor = null;
        if (key.includes(">")) {
          [key, anchor] = key.split(beforeRe);
          delta = 0;
        } else if (key.includes("<")) {
          [anchor, key] = key.split(afterRe);
          delta = 1;
        }
        if (key in dest) {
          if (srcVal && dest[key] && merge) {
            options.key = key;
            srcVal = merge(dest[key], srcVal, options);
          }
          dest[key] = srcVal;
        } else if (!anchor) {
          dest[key] = srcVal;
          indexMap == null ? void 0 : indexMap.set(key, indexMap.size);
        } else {
          if (!indexMap) {
            indexMap = /* @__PURE__ */ new Map();
            index = 0;
            for (const k in dest) {
              indexMap.set(k, index++);
            }
          }
          index = indexMap.get(anchor);
          dest[key] = srcVal;
          if (index == null && delta) {
            index = indexMap.size;
          } else {
            shuffle = shuffle || [];
            index = (index || 0) + delta;
            for (const item of indexMap) {
              const [k, v] = item;
              if (index <= v) {
                shuffle && (shuffle[indexMap.size - v - 1] = k);
                indexMap.set(k, v + 1);
              }
            }
            if (shuffle) {
              while (shuffle.length) {
                const k = shuffle.pop(),
                  v = dest[k];
                delete dest[k];
                dest[k] = v;
              }
            }
          }
          indexMap.set(key, index);
        }
      }
    }
    return dest;
  }
  /**
   * Sets value for a given path in the object
   * @param {Object} object Target object
   * @param {String} path Dot-separated path, e.g. 'object.childObject.someKey'
   * @param {*} value Value for a given path
   * @returns {Object} Returns passed object
   */
  static setPath(object, path, value) {
    path.split(".").reduce((result, key, index, array) => {
      const isLast = index === array.length - 1;
      if (isLast) {
        return (result[key] = value);
      } else if (!(result[key] instanceof Object)) {
        result[key] = {};
      }
      return result[key];
    }, object);
    return object;
  }
  static typeOf(value) {
    let trueType, type;
    if (value === null) {
      type = "null";
    } else if (value !== value) {
      type = "nan";
    } else {
      type = typeof value;
      if (type === "object") {
        if (value.isBase) {
          type = "instance";
        } else if (Array.isArray(value)) {
          type = "array";
        } else if (!(type = typeCache[(trueType = toString.call(value))])) {
          typeCache[trueType] = type = trueType.slice(8, -1).toLowerCase();
        }
      } else if (type === "function" && value.isBase) {
        type = "class";
      }
    }
    return type;
  }
};
Object.defineProperty(Objects, "hasOwn", {