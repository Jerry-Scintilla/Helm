;(function (global) {
  var HelmSDK = {
    _token: null,
    _apiBase: null,
    _locale: null,

    /**
     * Initialize the SDK. Call this once when the plugin page loads.
     * onReady(ctx) is called with { token, apiBase, locale } when Helm sends the init payload.
     */
    init: function (onReady) {
      window.addEventListener('message', function (event) {
        var data = event.data
        if (!data || typeof data.type !== 'string') return

        if (data.type === 'helm:init') {
          HelmSDK._token = data.payload.token
          HelmSDK._apiBase = data.payload.apiBase
          HelmSDK._locale = data.payload.locale || null
          if (typeof onReady === 'function') onReady(data.payload)
        }

        if (data.type === 'helm:token:refreshed') {
          HelmSDK._token = data.payload.token
        }
      })

      // Signal to parent that iframe is ready to receive init payload
      window.parent.postMessage({ type: 'helm:ready' }, '*')
    },

    /** Returns the current JWT access token. */
    getToken: function () {
      return HelmSDK._token
    },

    /** Returns the API base URL, e.g. "http://localhost:8000". */
    getApiBase: function () {
      return HelmSDK._apiBase
    },

    /**
     * Returns the current UI locale ('zh' or 'en').
     * Priority: helm:init payload → URL ?lang= param → default 'zh'.
     */
    getLocale: function () {
      return HelmSDK._locale ||
        new URLSearchParams(window.location.search).get('lang') ||
        'zh'
    },

    /**
     * Navigate the main Helm application to a named Vue route.
     * @param {string} route - Vue Router route name
     */
    navigate: function (route) {
      window.parent.postMessage({ type: 'helm:navigate', payload: { route: route } }, '*')
    },

    /**
     * Request a fresh token from the parent when the current token has expired.
     * The parent will reply with helm:token:refreshed.
     */
    requestTokenRefresh: function () {
      window.parent.postMessage({ type: 'helm:token:expired' }, '*')
    },
  }

  global.HelmSDK = HelmSDK
})(window)
