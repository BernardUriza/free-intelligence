  return value;
};

// ../Core/lib/Core/helper/BrowserHelper.js
var _a;
var BrowserHelper = class {
  static cacheFlags(
    platform = navigator.platform,
    userAgent = navigator.userAgent,
  ) {
    const me = this;
    me._isLinux = Boolean(platform.match(/Linux/));
    me._isMac = Boolean(platform.match(/Mac/));
    me._isWindows = Boolean(platform.match(/Win32/));
    me._isMobile = Boolean(
      userAgent.match(/Mobile|Opera Mini|Opera Mobi|Puffin/) ||
      typeof globalThis.orientation === "number",
    );
    me._isWebkit = Boolean(
      userAgent.match(/WebKit/) && !userAgent.match(/Edg/),
    );
    me._firefoxVersion = me.getVersion(userAgent, /Firefox\/(\d+)\./);
    me._isFirefox = me._firefoxVersion > 0;
    me._chromeVersion = me.getVersion(userAgent, /Chrom(?:e|ium)\/(\d+)\./);
    me._isChrome = me._chromeVersion > 0;
    me._isSafari = Boolean(userAgent.match(/Safari/)) && !me._isChrome;
    me._isMobileSafari = Boolean(userAgent.match(/Mobile.*Safari/));
    me._safariVersion = me.getVersion(userAgent, /Version\/(.*).Safari/);
    me._isAndroid = Boolean(userAgent.match(/Android/g));
  }
  //endregion
  //region Device
  /**
   * Yields `true` if the current browser supports CSS style `overflow:clip`.
   * @property {Boolean}
   * @readonly
   * @internal
   */
  static get supportsOverflowClip() {
    if (this._supportsOverflowClip == null) {
      const div = document.createElement("div");
      div.style.overflow = "clip";
      div.style.display = "none";
      document.documentElement.appendChild(div);
      this._supportsOverflowClip =
        div.ownerDocument.defaultView
          .getComputedStyle(div)
          .getPropertyValue("overflow") === "clip";
      div.remove();
    }
    return this._supportsOverflowClip;
  }
  /**
   * Yields `true` if the current browser supports CSS style `position:sticky`.
   * @property {Boolean}
   * @readonly
   * @internal
   */
  static get supportsSticky() {
    return true;
  }
  /**
   * Returns matched version for userAgent.
   * @param {String} versionRe version match regular expression
   * @returns {Number} matched version
   * @readonly
   * @internal
   */
  static getVersion(userAgent, versionRe) {
    const match = userAgent.match(versionRe);
    return match ? parseFloat(match[1]) : 0;
  }
  /**
   * Determines if the user is using a touch device.
   * @property {Boolean}
   * @readonly
   * @internal
   */
  static get isTouchDevice() {
    if (this._isTouchDevice === void 0) {
      this._isTouchDevice = globalThis.matchMedia(
        "(any-pointer:coarse)",
      ).matches;
    }
    return this._isTouchDevice;
  }
  // Reports true by default for our tests
  static get isHoverableDevice() {
    if (this._isHoverableDevice === void 0) {
      this._isHoverableDevice =
        globalThis.matchMedia("(any-hover: hover)").matches;
    }
    return this._isHoverableDevice;
  }
  //endregion
  //region Platform
  static get isBrowserEnv() {
    return typeof window !== "undefined";
  }
  /**
   * Checks if platform is Mac.
   * @property {Boolean}
   * @readonly
   * @category Platform
   */
  static get isMac() {
    return this._isMac;
  }
  /**
   * Checks if platform is Windows.
   * @property {Boolean}
   * @readonly
   * @category Platform
   */
  static get isWindows() {
    return this._isWindows;
  }
  /**
   * Checks if platform is Linux.
   * @property {Boolean}
   * @readonly
   * @category Platform
   */
  static get isLinux() {
    return this._isLinux;
  }
  /**
   * Checks if platform is Android.
   * @property {Boolean}
   * @readonly
   * @category Platform
   */
  static get isAndroid() {
    return this._isAndroid;
  }
  //endregion
  //region Browser
  /**
   * Checks if browser is Webkit.
   * @property {Boolean}
   * @readonly
   * @category Browser
   */
  static get isWebkit() {
    return this._isWebkit;
  }
  /**
   * Checks if browser is Chrome or Chromium based browser.
   * Returns truthy value for Edge Chromium.
   * @property {Boolean}
   * @readonly
   * @category Browser
   */
  static get isChrome() {
    return this._isChrome;
  }
  /**
   * Returns the major Chrome version or 0 for other browsers.
   * @property {Number}
   * @readonly
   * @category Browser
   */
  static get chromeVersion() {
    return this._chromeVersion;
  }
  /**
   * Checks if browser is Firefox.
   * @property {Boolean}
   * @readonly
   * @category Browser
   */
  static get isFirefox() {
    return this._isFirefox;
  }
  /**
   * Returns the major Firefox version or 0 for other browsers.
   * @property {Number}
   * @readonly
   * @category Browser
   */
  static get firefoxVersion() {
    return this._firefoxVersion;
  }
  /**
   * Checks if browser is Safari.
   * @property {Boolean}
   * @readonly
   * @category Browser
   */
  static get isSafari() {
    return this._isSafari;
  }
  static get safariVersion() {
    return this._safariVersion;
  }
  /**
   * Checks if browser is mobile Safari
   * @property {Boolean}
   * @readonly
   * @category Browser
   */
  static get isMobileSafari() {
    return this._isMobileSafari;
  }
  /**
   * Checks if the active device is a mobile device
   * @property {Boolean}
   * @readonly
   * @category Browser
   */
  static get isMobile() {
    return this._isMobile;
  }
  static get platform() {
    const me = this;
    return me._isLinux
      ? "linux"
      : me._isMac
        ? "mac"
        : me._isWindows
          ? "windows"
          : me._isAndroid
            ? "android"
            : me._isMobileSafari
              ? "ios"
              : null;
  }
  /**
   * Returns `true` if the browser supports passive event listeners.
   * @property {Boolean}
   * @internal
   * @deprecated Since 5.0. All modern browsers now support passive event listeners.
   * @category Browser
   */
  static get supportsPassive() {
    return true;
  }
  // Only works in secure contexts
  static get supportsRandomUUID() {
    if (this._supportsRandomUUID === void 0) {
      try {
        this._supportsRandomUUID = Boolean(
          globalThis.crypto.randomUUID().length > 0,
        );
      } catch (e) {
        this._supportsRandomUUID = false;
      }
    }
    return this._supportsRandomUUID;
  }
  //endregion
  //region Storage
  // https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API/Using_the_Web_Storage_API
  static get storageAvailable() {
    let storage, x;
    try {
      storage = localStorage;
      x = "__storage_test__";
      storage.setItem(x, x);
      storage.removeItem(x);
      return true;
    } catch (e) {
      return (
        e instanceof DOMException && // everything except Firefox
        (e.code === 22 || // Firefox
          e.code === 1014 || // test name field too, because code might not be present
          // everything except Firefox
          e.name === "QuotaExceededError" || // Firefox
          e.name === "NS_ERROR_DOM_QUOTA_REACHED") && // acknowledge QuotaExceededError only if there's something already stored
        storage.length !== 0
      );
    }
  }
  static setLocalStorageItem(key, value) {
    this.storageAvailable && localStorage.setItem(key, value);
  }
  static getLocalStorageItem(key) {
    return this.storageAvailable && localStorage.getItem(key);
  }
  static removeLocalStorageItem(key) {
    this.storageAvailable && localStorage.removeItem(key);
  }
  //endregion
  //region Helpers
  /**
   * Returns parameter value from search string by parameter name.
   * @param {String} paramName search parameter name
   * @param {String} [defaultValue] default value if parameter not found
   * @param {String} [search] search string. Defaults to `document.location.search`
   * @returns {String} search parameter string value
   * @category Helper
   */
  static searchParam(
    paramName,
    defaultValue2 = null,
    search = document.location.search,
  ) {
    const re = new RegExp(`[?&]${paramName}=?([^&]*)`),
      match = search.match(re);
    return (match && match[1]) || defaultValue2;
  }
  /**
   * Returns cookie by name.
   * @param {String} name cookie name
   * @returns {String} cookie string value
   * @category Helper
   */
  static getCookie(name) {
    const nameEq = encodeURIComponent(name) + "=",
      cookieItems = document.cookie.split(";");
    for (let i = 0; i < cookieItems.length; i++) {
      let c = cookieItems[i];
      while (c.charAt(0) === " ") {
        c = c.substring(1, c.length);
      }
      if (c.indexOf(nameEq) === 0) {
        return decodeURIComponent(c.substring(nameEq.length, c.length));
      }
    }
    return "";
  }
  /**
   * Triggers a download of a file with the specified name / URL.
   * @param {String} filename The filename of the file to be downloaded
   * @param {String} [url] The URL where the file is to be downloaded from
   * @internal
   * @category Download
   */
  static download(filename, url) {
    const a = document.createElement("a");
    a.download = filename;
    a.href = url || filename;
    a.style.cssText = "display:none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
  /**
   * Triggers a download of a Blob with the specified name.
   * @param {Blob} blob The Blob to be downloaded
   * @param {String} filename The filename of the file to be downloaded
   * @internal
   * @category Download
   */
  static downloadBlob(blob, filename) {
    const url = globalThis.URL.createObjectURL(blob);
    this.download(filename, url);
    globalThis.URL.revokeObjectURL(url);
  }
  static get queryString() {
    var _a4;
    const params = new URL(globalThis.location.href).searchParams;
    return (_a4 = Object.fromEntries) == null
      ? void 0
      : _a4.call(Object, params.entries());
  }
  // Used by docs fiddle
  static copyToClipboard(code) {
    let success2 = true;
    const textArea = document.createElement("textarea");
    textArea.value = code;
    textArea.style.height = textArea.style.width = 0;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand("copy");
    } catch (e) {
      success2 = false;
    }
    textArea.remove();
    return success2;
  }
  static isBryntumOnline(searchStrings) {
    searchStrings = Array.isArray(searchStrings)
      ? searchStrings
      : [searchStrings];
    return Boolean(
      /^(www\.)?bryntum\.com/.test(globalThis.location.host) ||
      (searchStrings == null
        ? void 0
        : searchStrings.some((str) => this.queryString[str] != null)),
    );
  }
  /**
   * Returns truthy value if page contains Content Security Policy meta tag or globalThis.bryntum.CSP is truthy value
   * @returns {Boolean}
   * @internal
   **/
  static get isCSP() {
    const { bryntum: bryntum2, document: document2 } = globalThis;
    if (bryntum2.CSP == null) {
      bryntum2.CSP = Boolean(
        document2.querySelector('meta[http-equiv="Content-Security-Policy"]'),
      );
    }
    return bryntum2.CSP;
  }
  //endregion
};
__publicField(