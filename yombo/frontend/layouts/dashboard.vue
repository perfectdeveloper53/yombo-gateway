<template>
  <div class="wrapper" :class="{'nav-open': $dashboardsidebar.showDashboardSidebar}">
    <notifications></notifications>
    <dashboard-side-bar>
      <template slot-scope="props" slot="links">
        <dashboard-sidebar-item :link="{name: 'Dashboard', icon: 'fas fa-home', path: '/dashboard'}">
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.devices'), icon: 'fas fa-wifi'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.list'), path: localePath('dashboard-devices')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.add'), path: localePath('dashboard-devices-add')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.discovered'), path: localePath('dashboard-devices-discovered')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.automation'), icon: 'fas fa-random'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.rules'), path: localePath('dashboard-automation_rules')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.scenes'), path: localePath('dashboard-scenes')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.crontab'), path: localePath('dashboard-crontab')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.info'), icon: 'fas fa-info'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.atoms'), path: localePath('dashboard-atoms')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.device_commands'), path: localePath('dashboard-device_commands')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.intents'), path: localePath('dashboard-intents')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.states'), path: localePath('dashboard-states')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.storage'), path: localePath('dashboard-storage')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.weblogs'), path: localePath('dashboard-webinterface_logs')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.statistics'), icon: 'fas fa-tachometer-alt', path: localePath('dashboard-statistics')}">
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.permissions'), icon: 'fas fa-user-shield'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.roles'), path: localePath('dashboard-permissions-roles')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.users'), path: localePath('dashboard-permissions-users')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.misc'), icon: 'fas fa-inbox'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.locations'), path: localePath('dashboard-locations')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.areas'), path: localePath('dashboard-areas')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.dns'), path: localePath('dashboard-settings-dns')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.encryption'), path: localePath('dashboard-settings-encryption')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.gateways'), path: localePath('dashboard-gateways')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.system'), icon: 'fas fa-cogs'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.overview'), path: localePath('dashboard-system-overview')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.configuration'), path: localePath('dashboard-configuration')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.backup'), path: localePath('dashboard-system-backup')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.common.status'), path: localePath('dashboard-system-status')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'MQTT', icon: 'far fa-envelope'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.send'), path: localePath('dashboard-mqtt')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.monitor'), path: localePath('dashboard-mqtt-monitor')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.debug'), icon: 'fas fa-bug'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.overview'), path: localePath('dashboard-debug')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.atoms'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'atoms'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.authentication_platforms'), path: localePath('dashboard-debug-authentication_platforms')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.automation_rules'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'automation_rules'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.cache'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'cache'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.commands'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'commands'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.devices'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'devices'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.device_command_types'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'device_command_types'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.device_types'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'device_types'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.gateways'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'gateways'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.hooks_called_libraries'), path: localePath('dashboard-debug-hooks_called_libraries')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.hooks_called_modules'), path: localePath('dashboard-debug-hooks_called_modules')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.http_event_stream'), path: localePath('dashboard-debug-http_event_stream')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.input_types'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'input_types'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.locations'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'locations'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.module_device_types'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'module_device_types'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.modules'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'modules'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.notifications'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'notifications'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.scenes'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'scenes'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.sqldict'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'sqldict'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.states'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'states'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.statistic_bucket_lifetimes'), path: localePath('dashboard-debug-statistic_bucket_lifetimes')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.states'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'states'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.storage'), path: localePath('dashboard-debug-storage')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.users'), path: localePath('dashboard-debug-users')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.variable_data'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'variables_data'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.variable_fields'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'variables_fields'} })}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.variable_groups'), path: localePath({name: 'dashboard-debug-generic-id', params: {id:'variables_groups'} })}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

      </template>
    </dashboard-side-bar>
    <div class="main-panel">
      <top-navbar></top-navbar>
      <router-view name="header"></router-view>
  <div class="panel-header panel-header-sm">
  </div>
      <div :class="{content: !$route.meta.hideContent}" @click="toggleSidebar">
        <zoom-center-transition :duration="150" mode="out-in">
          <!-- your content here -->
          <router-view></router-view>
        </zoom-center-transition>
      </div>
      <content-footer v-if="!$route.meta.hideFooter"></content-footer>
    </div>
  </div>
</template>

<script>
/* eslint-disable no-new */
import PerfectScrollbar from 'perfect-scrollbar';
import 'perfect-scrollbar/css/perfect-scrollbar.css';

function hasElement(className) {
  return document.getElementsByClassName(className).length > 0;
}

function initScrollbar(className) {
  if (hasElement(className)) {
    new PerfectScrollbar(`.${className}`);
  } else {
    // try to init it later in case this component is loaded async
    setTimeout(() => {
      initScrollbar(className);
    }, 100);
  }
}

import TopNavbar from '@/layouts/Dashboard/TopNavbar.vue';
import ContentFooter from '@/layouts/Dashboard/ContentFooter.vue';
import DashboardContent from '@/layouts/Dashboard/Content.vue';
import MobileMenu from '@/layouts/Dashboard/Extra/MobileMenu.vue';
import { SlideYDownTransition, ZoomCenterTransition } from 'vue2-transitions';

export default {
  components: {
    TopNavbar,
    ContentFooter,
    DashboardContent,
    MobileMenu,
    // UserMenu,
    SlideYDownTransition,
    ZoomCenterTransition
  },
  methods: {
    toggleSidebar() {
      if (this.$dashboardsidebar.showDashboardSidebar) {
        this.$dashboardsidebar.displayDashboardSidebar(false);
      }
    }
  },
  mounted() {
    let docClasses = document.body.classList;
    let isWindows = navigator.platform.startsWith('Win');
    if (isWindows) {
      // if we are on windows OS we activate the perfectScrollbar function
      initScrollbar('sidebar');
      initScrollbar('sidebar-wrapper');

      docClasses.add('perfect-scrollbar-on');
    } else {
      docClasses.add('perfect-scrollbar-off');
    }
  }
};
</script>
<style lang="scss">
$scaleSize: 0.95;
@keyframes zoomIn95 {
  from {
    opacity: 0;
    transform: scale3d($scaleSize, $scaleSize, $scaleSize);
  }
  to {
    opacity: 1;
  }
}
.main-panel .zoomIn {
  animation-name: zoomIn95;
}
@keyframes zoomOut95 {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
    transform: scale3d($scaleSize, $scaleSize, $scaleSize);
  }
}
.main-panel .zoomOut {
  animation-name: zoomOut95;
}
</style>
