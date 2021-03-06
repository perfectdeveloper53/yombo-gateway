import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/devices')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/devices')
    },
    fetchOne(id) {
        // console.log("devices find: " + id);
        return yboapiv1().get('/devices/' + id);
    },
    delete(id, data) {
        // console.log("devices delete: " + id);
        // console.log(data);
        return yboapiv1().delete('/devices/' + id);
    },
    patch(id, data) {
        // console.log("devices patch: " + id);
        // console.log(data);
        return yboapiv1().patch('/devices/' + id, data);
    },
}
