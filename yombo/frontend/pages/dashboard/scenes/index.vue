<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <div class="fa-pull-right">
            <nuxt-link class="navbar-brand fa-pull-right" :to="localePath('dashboard-devices-add')">
              <button type="button" class="btn btn-info btn-sm" data-dismiss="modal">
                <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new</a>
                </button>
            </nuxt-link>
            <br>
            <el-input
                  class="fa-pull-right"
                  v-model="search"
                  size="mini"
                  :placeholder="$t('ui.common.search_ddd')"/>
          </div>
          <h4 class="card-title">
            {{ $t('ui.navigation.scenes') }}
          </h4>
          <last-updated refresh="gateway/scenes/fetch" getter="gateway/scenes/display_age"/>
        </div>
        <div class="card-body">
          <el-table
            :data="scenes"
          >
            <el-table-column :label="$t('ui.common.label')" property="label"></el-table-column>
            <el-table-column :label="$t('ui.common.description')" property="rule.config.description"></el-table-column>
            <el-table-column :label="$t('ui.common.enabled')">
              <div slot-scope="props">
                {{props.row.rule.config.enabled == true}}
              </div>
            </el-table-column>
            <el-table-column :label="$t('ui.common.created_at')" property="created_at"></el-table-column>
            <el-table-column :label="$t('ui.common.updated_at')" property="updated_at"></el-table-column>
            <el-table-column
              align="right" :label="$t('ui.common.actions')">
              <div slot-scope="props" class="table-actions">
                <action-details path="dashboard-scenes-details" :id="props.row.id"/>
                <action-edit path="dashboard-scenes-edit" :id="props.row.id"/>
                <template v-if="props.row.rule.config.enabled == true">
                  <action-disable dispatch="yombo/scenes/disable" :id="props.row.id"
                               i18n="scene" :item_label="props.full_label"/>
                </template>
                <template v-else>
                  <action-enable dispatch="yombo/scenes/enable" :id="props.row.id"
                               i18n="scene" :item_label="props.full_label"/>
                </template>

                <action-delete dispatch="yombo/scenes/delete" :id="props.row.id"
                               i18n="scene" :item_label="props.full_label"/>
              </div>
            </el-table-column>
          </el-table>
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import { ActionDelete, ActionDetails, ActionDisable, ActionEdit, ActionEnable } from '@/components/Dashboard/Actions';
import LastUpdated from '@/components/Dashboard/LastUpdated.vue'

import { Table, TableColumn } from 'element-ui';

import Device from '@/models/device'

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    ActionDelete,
    ActionDetails,
    ActionDisable,
    ActionEdit,
    ActionEnable,
    LastUpdated,
  },
  data() {
    return {
      search: '',
    };
  },
  computed: {
    scenes () {
      let source = this.$store.state.gateway.scenes.data;
      let results = [];

      Object.keys(source).forEach(key => {
        results.push(source[key]);
      });

      return results
    },
  },
  mounted () {
    this.$store.dispatch('gateway/scenes/refresh');
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },
};
</script>
