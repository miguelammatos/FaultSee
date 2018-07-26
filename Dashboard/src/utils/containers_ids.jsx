const NUMBER_LETTERS = 12

class Containers_IDS {

  Load(json_array) {
      const containers = {}
      const services = {}
      for (var index = 0; index < json_array.length; ++index) {
          var container_information = json_array[index]
          var container_id = container_information["container_id"].substring(0, NUMBER_LETTERS)
          var service_name = container_information["service"]
          var slot_number = container_information["slot"]

          containers[container_id] = {
            disabled: false,
            service: service_name,
            slot: slot_number,
          }
          var service_info = services[service_name] || {}
          service_info[container_id] = {
              disabled: false,
              slot: slot_number,
          }
          services[service_name] = service_info
      }
      console.log(containers)

      this.containers_info = containers
      this.service_info = services
      return this
  }

  get_containers_ids() {
      return this.containers_info
  }
  get_service_info() {
      return this.service_info
  }

}


export default Containers_IDS
