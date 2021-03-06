/**
 * All items loaded here will be globally available within the app.
 */
import Vue from 'vue'

// Sweet alerts for veu
// import VueSweetalert2 from 'vue-sweetalert2';
// Notifications plugin. Used on Notifications page
import Notifications from '@/components/Common/NotificationPlugin';
// Validation plugin used to validate forms
import VeeValidate from 'vee-validate';
// A plugin file where you could register global components used across the app
import GlobalComponents from './globalComponents';
// A plugin file where you could register global directives
import GlobalDirectives from './globalDirectives';
// Sidebar on the right. Used as a local plugin in DashboardLayout.vue
import DashboardSideBar from '@/components/Dashboard/DashboardSidebarPlugin';

import GatewayApiV1 from '@/services/gwapiv1/GatewayApiV1'
import YomboApiV1 from '@/services/yboapiv1/YomboApiV1'

// element ui language configuration
import lang from 'element-ui/lib/locale/lang/en';
import locale from 'element-ui/lib/locale';
locale.use(lang);

import VueTemperatureFilter from 'vue-temperature-filter';
// Add Global Configuration
Vue.use(VueTemperatureFilter, {
  fromFahrenheit: true,
  showText: true
});

import axios from 'axios'

async function getEnv() {
  let response = await axios.get('/nuxt.env');
  let env = {};
  if (typeof response.data === 'string') {
    env = JSON.parse(response.data);
  } else {
    env = response.data;
  }
  // process.env.gwenv = env;
  Object.defineProperty(process.env, 'gwenv', {value: env});
  Object.defineProperty(Vue.prototype, '$gwenv', {value: env});
}

getEnv();

export default () => {
  Object.defineProperty(Vue.prototype, '$gwapiv1', { value: GatewayApiV1 });
  Object.defineProperty(Vue.prototype, '$yboapiv1', { value: YomboApiV1 });
  // console.log(Object.keys(window));
}

Vue.use(GlobalComponents);
Vue.use(GlobalDirectives);
Vue.use(DashboardSideBar);
Vue.use(Notifications);
Vue.use(VeeValidate, { fieldsBagName: 'veeFields' });
