// Page transitions via the View Transitions API — a cross-fade between routes, plus shared-element
// "container transform" morphs for any element that carries a matching `view-transition-name` on both
// the old and new page (e.g. a product image morphing from the grid into the PDP). Gracefully no-ops
// where the API is unsupported or the user prefers reduced motion.
import { nextTick } from "vue";
import type { Router } from "vue-router";

const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function installViewTransitions(router: Router): void {
  if (!("startViewTransition" in Document.prototype)) return; // Firefox / older Safari → plain nav

  router.beforeResolve((to, from) => {
    // skip the initial load, in-place navigations, and reduced-motion users
    if (!from.name || to.path === from.path || reducedMotion()) return;

    return new Promise<void>((unblock) => {
      document.startViewTransition(() => {
        // 1) let this guard resolve so the navigation actually commits…
        unblock();
        // 2) …then hold the transition's snapshot until the NEW route has rendered. afterEach fires
        //    once navigation is committed; nextTick waits for Vue to flush the new view to the DOM.
        //    (Resolving on a bare nextTick races the router and captures no change → no morph.)
        return new Promise<void>((rendered) => {
          const stop = router.afterEach(() => {
            stop();
            void nextTick(() => rendered());
          });
        });
      });
    });
  });
}
