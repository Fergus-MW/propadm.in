// PostHog's official async bootstrap; the project token comes from runtime config.
!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],Object.defineProperty(u,"toString",{configurable:!0,enumerable:!0,writable:!0,value:function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}}),Object.defineProperty(u.people,"toString",{configurable:!0,enumerable:!0,writable:!0,value:function(){return u.toString(1)+".people (stub)"}}),o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagResult isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);

const cleanUrl = (value) => {
  try { const url = new URL(value); return `${url.origin}${url.pathname}`; }
  catch { return ""; }
};
const sanitizeProperties = (properties) => {
  for (const [key, value] of Object.entries(properties)) {
    if (typeof value === "string" && (key.endsWith("_url") || key.endsWith("referrer")))
      properties[key] = cleanUrl(value);
    else if (value && typeof value === "object" && !Array.isArray(value))
      sanitizeProperties(value);
  }
};
const ready = fetch("/api/analytics-config", { cache: "no-store" })
  .then(async (response) => {
    if (!response.ok) return false;
    const config = await response.json();
    if (!config.projectToken?.startsWith("phc_")) return false;
    window.posthog.init(config.projectToken, {
      api_host: config.host,
      ui_host: "https://us.posthog.com",
      defaults: "2026-05-30",
      autocapture: false,
      capture_dead_clicks: false,
      capture_heatmaps: false,
      capture_performance: false,
      disable_surveys: true,
      capture_pageview: false,
      capture_pageleave: false,
      disable_session_recording: true,
      person_profiles: "never",
      advanced_disable_feature_flags: true,
      before_send: (event) => {
        if (!event) return event;
        if (!["$pageview", "landing_signup_submitted", "landing_signup_failed", "landing_signup_completed", "landing_signup_cta_clicked"].includes(event.event)) return null;
        event.properties.surface = "landing";
        event.properties.environment = config.environment;
        sanitizeProperties(event);
        return event;
      },
    });
    window.posthog.register({ surface: "landing", environment: config.environment });
    window.posthog.capture("$pageview", { $current_url: cleanUrl(window.location.href) });
    return true;
  }).catch(() => false);

window.captureAnalytics = (event, properties = {}) => {
  void ready.then((enabled) => { if (enabled) window.posthog.capture(event, properties); });
};
