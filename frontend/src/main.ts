import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router";
import "./style.css";

// iOS Safari ignores user-scalable=no in a browser tab, so stop pinch zoom here too (installed to
// the home screen, the viewport meta already does it).
document.addEventListener("gesturestart", (event) => event.preventDefault());

createApp(App).use(router).mount("#app");
