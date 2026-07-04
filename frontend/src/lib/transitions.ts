// Elements sharing a `view-transition-name` on both pages get a shared-element morph for free.
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
      try {
        document.startViewTransition(() => {
          // Must unblock (commit the nav) before waiting for the new view to render — otherwise
          // the transition captures no DOM change and there's no morph.
          unblock();
          return new Promise<void>((rendered) => {
            const stop = router.afterEach(() => {
              stop();
              void nextTick(() => rendered());
            });
          });
        });
      } catch {
        unblock(); // API threw synchronously → fall through to a plain navigation, never drop it
      }
    });
  });
}
