import React, { Component } from "react";
import { Table, Grid, Row, Col } from "react-bootstrap";

import Card from "components/Card/Card";

import Button from "components/CustomButton/CustomButton";

import ToggleButton from 'components/ToggleButton/ToggleButton'

import FilterableTable from 'components/FilterableTable/FilterableTable'
import ServiceCard from 'components/ServiceCard/ServiceCard'
// import ContainerCard from 'components/ContainerCard/ContainerCard'
import { useTable, useFilters } from 'react-table'

import Containers_IDS from "utils/containers_ids"

import * as array_data_json from "variables/containers_logs.json"
import * as array_ids_json from "variables/containers_ids.json"

const array_ids = array_ids_json.default
const array_data = array_data_json.default

// const {array_data} = array_data_json;

// import {
//   useTable,
//   useGroupBy,
//   useFilters,
//   useSortBy,
//   useExpanded,
//   usePagination,
//   ...
// } from 'react-table'

// traducao container_id para service - slot

const NUMBER_LETTERS = 12

class Logs extends Component {
    constructor(props) {
        super(props);
        this.container_filter = this.container_filter.bind(this)


        this.state = {
            containers: {
            },
            services: {

            },
            columns: [
                      {
                        Header: 'Moment',
                        accessor: 'time',
                      },
                      {
                        Header: 'Container',
                        accessor: 'container_id',
                        filter: this.container_filter
                      },
                      {
                        Header: 'Log',
                        accessor: 'msg',
                      },
                    ],
            data: this.load_logs_json(),
            hide_code: true
        };
    }

    load_logs_json(){
      for (var index = 0; index < array_data.length; ++index) {
          array_data[index].container_id = array_data[index].container_id.substring(0, NUMBER_LETTERS)
          array_data[index].time = array_data[index].time  // we receive time in microseconds
      }
      return array_data
    }

    load_containers_ids(){
      var loader = new Containers_IDS().Load(array_ids)
      this.setState({ containers: loader.get_containers_ids(),
                      services: loader.get_service_info(),
            });
    }

    container_filter(rows, id, filterValue) {
      return rows.filter(row => {
          const rowValue = row.values[id];
          if (this.state.containers[rowValue] != undefined) {
            return !this.state.containers[rowValue].disabled
          };
          return false;
    })}

    componentDidMount() {
        this.load_containers_ids()
    }

    // ------------------------------------------------
    //  toggles to control which containers to show
    // ------------------------------------------------

    toggle_container(container_id) {
        let tmp_containers = this.state.containers;
        tmp_containers[container_id].disabled = !tmp_containers[container_id].disabled;
        this.setState({ containers: tmp_containers });
    }

    only_this_container(container_id) {
      var tmp_containers = this.state.containers;
      var containers_ids = Object.keys(this.state.containers)
      for (var index = 0; index < containers_ids.length; ++index) {

          var show_this_one = containers_ids[index] == container_id

          var container_info = tmp_containers[containers_ids[index]]
          container_info.disabled = show_this_one ? false : true
      }
      this.setState({ containers: tmp_containers });
    }
    only_this_service(service) {
      var tmp_containers = this.state.containers;
      var containers_ids = Object.keys(this.state.containers)
      for (var index = 0; index < containers_ids.length; ++index) {

          var show_this_one = tmp_containers[containers_ids[index]].service == service

          var container_info = tmp_containers[containers_ids[index]]
          container_info.disabled = show_this_one ? false : true
      }
      this.setState({ containers: tmp_containers });
    }
    change_all_service(service, new_disabled_state) {
      var tmp_containers = this.state.containers;
      var containers_ids = Object.keys(this.state.containers)
      for (var index = 0; index < containers_ids.length; ++index) {
          var this_one_applies = tmp_containers[containers_ids[index]].service == service
          var container_info = tmp_containers[containers_ids[index]]
          container_info.disabled = this_one_applies ? new_disabled_state : container_info.disabled
      }
      this.setState({ containers: tmp_containers });
    }
    hide_all_service(service) {
        this.change_all_service(service, true)
    }
    show_all_service(service) {
        this.change_all_service(service, false)
    }


    // ------------------------------------------------
    // ------------------------------------------------
    // ------------------------------------------------

    toggle_code() {
      this.setState({hide_code: !this.state.hide_code})
    }


    render() {
      return <div className="content">
        <Grid fluid>

          <Row>
              {Object.keys(this.state.services).map((service_name, index) =>
                  <ServiceCard
                      key={service_name}
                      service={service_name}
                      hide_all_containers_click={() => this.hide_all_service.bind(this)(service_name)}
                      show_all_containers_click={() => this.show_all_service.bind(this)(service_name)}
                      only_this_service_click={() => this.only_this_service.bind(this)(service_name)}
                      containers={this.state.containers}
                      handle_click_only_this_container={this.only_this_container.bind(this)}
                      handle_click_toggle_container={this.toggle_container.bind(this)}
                    />
              )}


          </Row>
          <Row>
            <button onClick={this.toggle_code.bind(this)} > {this.state.hide_code ? "Show" : "Hide"} Filters </button>
            <div id="demo" className={"collapse" + (this.state.hide_code ? '' : ' in')}>
              <pre>
                 <code>
                   {JSON.stringify(this.state.containers,
                     null,
                     2
                   )}
                 </code>
               </pre>
             </div>
          </Row>
          <Row>

            <Col md={12}>
              <Card
                // title="Striped Table with Hover"
                // category="Here is a subtitle for this table"
                ctTableFullWidth
                ctTableResponsive
                content={
                  <FilterableTable columns={this.state.columns} data={this.state.data}/>
                }
              />
            </Col>
          </Row>
        </Grid>
      </div>
    }
}

export default Logs;
