<template>
  <section class="Devices">
    <div class="container">
      <div class="header">
        <h2 class="title">DEVICES</h2>
        <button class="button" @click="add">ADD DEVICE</button>
      </div>

      <DevicesList />
    </div>
  </section>
</template>

<script>
import User from '@/models/User'
import UsersList from './UsersList'

export default {
  components: {
    UsersList
  },

  methods: {
    add () {
      User.insert({
        data: { name: '' }
      })
    }
  }
}
</script>

<style scoped>
@import "@/assets/styles/variables";

.container {
  border-radius: 4px;
  background-color: #fff;
  overflow: hidden;
  box-shadow: var(--shadow-depth-3);
}

.header {
  display: flex;
  justify-content: space-between;
  padding: 16px 24px;
}

.title {
  line-height: 32px;
  font-size: 16px;
  color: var(--c-gray);
}

.button {
  border: 1px solid var(--c-gray-light);
  border-radius: 2px;
  padding: 0 16px;
  line-height: 30px;
  font-size: 12px;
  color: var(--c-gray);
  transition: all .3s;

  &:hover {
    border-color: var(--c-gray);
    color: var(--c-black);
  }
}
</style>
