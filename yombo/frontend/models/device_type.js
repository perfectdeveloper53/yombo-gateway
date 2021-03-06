import { Model } from '@vuex-orm/core'

export default class Device_Type extends Model {
  static entity = 'device_types';

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      original_user_id: this.string(''),
      category_id: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      platform: this.string(''),
      public: this.number(0),
      status: this.number(0),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
