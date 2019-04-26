export const state = () => ({
  categories: {},
  last_download_at: 0
});

export const actions = {
  fetch( { commit }) {
    dispatch('locations/refresh', {}, {root:true});
    let response;
    try {
      response = window.$nuxt.$yboapiv1.categories().all()
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
      this.$bus.$emit('messageSent', 'over there');
    if (state.last_download_at <= Math.floor(Date.now()/1000) - 3600) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, data) {
    state.categories = {}
    Object.keys(data).forEach(key => {
      state.categories[data[key]['id']] = data[key]['attributes']
    });
    state.last_download_at = Math.floor(Date.now() / 1000);
  }
};

export const getters =  {
  fullLabel: (state) => (id) => {
    let item = state.devices.devices[id];

    if
    return state.locations.locations[]
  }
};
