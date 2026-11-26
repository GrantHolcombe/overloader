import { createRouter, createWebHistory } from "vue-router";
import { session } from "./lib/session";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/signin", component: () => import("./views/SignInView.vue"), meta: { public: true } },
    { path: "/", component: () => import("./views/HomeView.vue") },
    {
      path: "/exercise/:id",
      component: () => import("./views/ExerciseView.vue"),
      props: (route) => ({ id: Number(route.params.id) }),
    },
    {
      path: "/exercise/:id/progress",
      component: () => import("./views/ProgressView.vue"),
      props: (route) => ({ id: Number(route.params.id) }),
    },
    { path: "/settings", component: () => import("./views/SettingsView.vue") },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach((to) => {
  if (!to.meta.public && !session.token) return { path: "/signin" };
  if (to.path === "/signin" && session.token) return { path: "/" };
});
