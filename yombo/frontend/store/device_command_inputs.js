import Device_Command_Input from '@/models/device_command_input'

export const state = () => ({
  last_download_at: 0
});

export const actions = {
  fetch( { commit, dispatch }) {
    let response;
    try {
      response = window.$nuxt.$yboapiv1.device_commands_inputs().allGW()
        .then(response => {
          commit('SET_DATA', response.data['data'])
        });
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
      return
    }
  },
  refresh( { state, dispatch }) {
      // this.$bus.$emit('messageSent', 'over there');
    if (state.last_download_at <= Math.floor(Date.now()/1000) - 3600) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, payload) {
    Device_Command_Input.deleteAll();
    Object.keys(payload).forEach(key => {
      Device_Command_Input.insert({
        data: payload[key]['attributes'],
      })
    });
    state.last_download_at = Math.floor(Date.now() / 1000);
  }
};
