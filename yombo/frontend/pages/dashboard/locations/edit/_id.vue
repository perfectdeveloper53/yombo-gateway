<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
           {{ $t('ui.common.edit_location') }}: {{item.label}}
          <div class="pull-right">
            <n-button @click.native="handleDelete(item)"
                      class="remove"
                      type="danger"
                      size="sm">
                {{ $t('ui.common.delete') }}
            </n-button>
          </div>
         </h4>
        </div>
        <div class="card-body">
          Location: {{id}}
          {{item}}
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import Location from '@/models/location'

export default {
  layout: 'dashboard',
  components: {
  },
  data() {
    return {
      id: this.$route.params.id,
      display_age: '0 seconds',
    };
  },
  computed: {
    item () {
      return Location.find(this.id)
    },
  },

  methods: {
    handleDelete(row) {
      this.$swal({
        title: this.$t('ui.prompt.delete_location'),
        text: this.$t('ui.phrase.cannot_undo'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, delete it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch('yombo/locations/delete', row.id);
          this.$swal({
            title: this.$t('ui.common.deleted'),
            text: `You deleted ${row.full_name}`,
            type: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
  },
  mounted () {
    this.$store.dispatch('yombo/locations/fetchOne', this.id);
  },
};
</script>
