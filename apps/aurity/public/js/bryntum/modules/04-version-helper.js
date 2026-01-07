    ((object, property) => hasOwnProperty2.call(object, property)),
});
Objects._$name = "Objects";

// ../Core/lib/Core/helper/VersionHelper.js
var VersionHelper = class _VersionHelper {
  /**
   * Set version for specified product
   * @private
   * @param {String} product
   * @param {String} version
   */
  static setVersion(product, version) {
    product = product.toLowerCase();
    VH[product] = {
      version,
      isNewerThan(otherVersion) {
        return _VersionHelper.semanticCompareVersion(
          otherVersion,
          version,
          "<",
        );
      },
      isOlderThan(otherVersion) {
        return _VersionHelper.semanticCompareVersion(
          otherVersion,
          version,
          ">",
        );
      },
    };
    let bundleFor = "";
    if (typeof productName !== "undefined") {
      bundleFor = productName;
    }
    const globalKey = `${bundleFor}.${product}${version.replace(/\./g, "-")}`;
    if (
      BrowserHelper.isBrowserEnv &&
      !globalThis.bryntum.silenceBundleException
    ) {
      if (globalThis.bryntum[globalKey] === true) {
        if (this.isTestEnv) {
          globalThis.BUNDLE_EXCEPTION = true;
        } else {
          let errorProduct = bundleFor || product;
          if (errorProduct === "core") {
            errorProduct = "grid";
          }
          let capitalized = StringHelper.capitalize(errorProduct);
          if (errorProduct === "schedulerpro") {
            capitalized = "SchedulerPro";
          }
          throw new Error(
            `The Bryntum ${capitalized} bundle was loaded multiple times by the application.

Common reasons you are getting this error includes:

* Imports point to different types of the bundle (e.g. *.module.js and *.umd.js)
* Imports point to both sources and bundle
* Imports do not use the shortest relative path, JS treats them as different files
* Cache busters differ between imports, JS treats ${errorProduct}.module.js?1 and ${errorProduct}.module.js?2 as different files
* Imports missing file type, verify they all end in .js

See https://bryntum.com/products/${errorProduct}/docs/guide/${capitalized}/gettingstarted/es6bundle#troubleshooting for more information

`,
          );
        }
      } else {
        globalThis.bryntum[globalKey] = true;
      }
    }
  }
  /**
   * Get (previously set) version for specified product
   * @private
   * @param {String} product
   */
  static getVersion(product) {
    product = product.toLowerCase();
    if (!VH[product]) {
      throw new Error(
        "No version specified! Please check that you import VersionHelper correctly into the class from where you call `deprecate` function.",
      );
    }
    return VH[product].version;
  }
  /**
   * Checks the version1 against the passed version2 using the comparison operator.
   * Supports `rc`, `beta`, `alpha` release states. Eg. `1.2.3-alpha-1`.
   * State which is not listed above means some version below `alpha`.
   * @param {String} version1 The version to test against
   * @param {String} version2 The version to test against
   * @param {String} [comparison] The comparison operator, `<=`, `<`, `=`, `>` or `>=`.
   * @returns {Boolean} `true` if the test passes.
   * @internal
   */
  static semanticCompareVersion(version1, version2, comparison = "=") {
    version1 = version1 || "";
    version2 = version2 || "";
    const version1Arr = version1.split(/[-.]/),
      version2Arr = version2.split(/[-.]/),
      isLower = comparison.includes("<"),
      normalizeArr = (arr, maxLength) => {
        const states = ["rc", "beta", "alpha"],
          result = arr.map((v) => {
            if (states.includes(v)) {
              return -states.indexOf(v) - 2;
            }
            const res = Number.parseInt(v);
            return Number.isNaN(res) ? -states.length : res;
          });
        while (result.length < maxLength) {
          result.push(-1);
        }
        return result;
      },
      compareArr = () => {
        const maxLength = Math.max(version1Arr.length, version2Arr.length),
          arr1 = normalizeArr(version1Arr, maxLength),
          arr2 = normalizeArr(version2Arr, maxLength);
        for (let i = 0; i < maxLength; i++) {
          if (arr1[i] !== arr2[i]) {
            return isLower ? arr1[i] < arr2[i] : arr1[i] > arr2[i];
          }
        }
        return true;
      };
    switch (comparison) {
      case "=":
        return version1 === version2;
      case "<=":
      case ">=":
        return version1 === version2 || compareArr();
      case "<":
      case ">":
        return version1 !== version2 && compareArr();
    }
    return false;
  }
  /**
   * Checks the passed product against the passed version using the passed test.
   * @param {String} product The name of the product to test the version of
   * @param {String} version The version to test against
   * @param {String} operator The test operator, `<=`, `<`, `=`, `>` or `>=`.
   * @returns {Boolean} `true` if the test passes.
   * @internal
   */
  static checkVersion(product, version, operator) {
    return _VersionHelper.semanticCompareVersion(
      VH.getVersion(product),
      version,
      operator,
    );
  }
  /**
   * Based on a comparison of current product version and the passed version this method either outputs a console.warn
   * or throws an error.
   * @param {String} product The name of the product
   * @param {String} invalidAsOfVersion The version where the offending code is invalid (when any compatibility layer
   * is actually removed).
   * @param {String} message Required! A helpful warning message to show to the developer using a deprecated API.
   * @internal
   */
  static deprecate(product, invalidAsOfVersion, message) {
    const justWarn = VH.checkVersion(product, invalidAsOfVersion, "<");
    if (justWarn) {
      console.warn(
        `Deprecation warning: You are using a deprecated API which will change in v${invalidAsOfVersion}. ${message}`,
      );
    } else {
      throw new Error(`Deprecated API use. ${message}`);
    }
  }
  /**
   * Returns truthy value if environment is in testing mode
   * @returns {Boolean}
   * @internal
   **/
  static get isTestEnv() {
    var _a4, _b, _c;
    const isTestEnv = Boolean(
      (_a4 = globalThis.bryntum) == null ? void 0 : _a4.isTestEnv,
    );
    try {
      return (
        isTestEnv ||
        Boolean(
          (_c = (_b = globalThis.parent) == null ? void 0 : _b.bryntum) == null
            ? void 0
            : _c.isTestEnv,
        )
      );
    } catch (e) {
      return isTestEnv;
    }
  }
  static get isDebug() {
    let result = false;
    return result;
  }
};
var VH = VersionHelper;