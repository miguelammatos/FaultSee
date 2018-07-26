import React, { Component } from "react";
import { Table, Grid, Row, Col } from "react-bootstrap";


import Card from "components/Card/Card";

import Button from "components/CustomButton/CustomButton";

import Plot from 'react-plotly.js';

import Containers_IDS from "utils/containers_ids"
import ServiceCard from 'components/ServiceCard/ServiceCard'
// import AveragePlot from 'components/AveragePlot/AveragePlot'


import * as array_stats_json from "variables/containers_stats.json"
import * as array_ids_json from "variables/containers_ids.json"

const array_stats = array_stats_json.default
const array_ids = array_ids_json.default

const NUMBER_LETTERS = 12


class GraphContainers extends Component {
  constructor(props) {
      super(props);
      this.state = {
            width: 0,
            graphs_height: 400,
            containers_data: {},

            containers: {
            },
            services: {

            },

            layout: {}, frames: [],
            config: {
                      scrollZoom: true,
                      toImageButtonOptions: {
                        format: 'svg', // one of png, svg, jpeg, webp
                        filename: 'custom_image',
                        scale: 1 // Multiply title/legend/axis/canvas sizes by this factor
                      },
                      showLink: true, // show "edit chart"
                      // showSendToCloud: true,
                      responsive: true
                },
            hide_code: true,
            };
  }

  componentDidMount() {
    this.load_containers_ids()
    this.load_containers_data(1)
    this.updateDimensions();
    window.addEventListener("resize", this.updateDimensions.bind(this));
  }
  updateDimensions() {
    this.setState({ width: window.innerWidth });
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

  load_containers_ids(){
    var loader = new Containers_IDS().Load(array_ids)
    this.setState({ containers: loader.get_containers_ids(),
                    services: loader.get_service_info(),
          });
  }
  roundMultiple(x, multiple)
  {
      return (x % multiple) >= (multiple/2) ? parseInt(x / multiple) * multiple + multiple : parseInt(x / multiple) * multiple;
  }

  load_containers_data(multiple_to_use) {
      var stats = {}
      // var data_template =

      // NOTE: Assuiming time sorted!!!
      for (var index = 0; index < array_stats.length; ++index) {
          var element = array_stats[index]
          var container_id = element.container_id

          // get holder

          var tmp_holder = (stats[container_id] || {
              time: [],
              cpu: [],
              mem: [],
              rx_bytes: [],
              rx_packets: [],
              rx_dropped: [],
              tx_bytes: [],
              tx_packets: [],
              tx_dropped: [],
              // read_and_write_bytes: [],
          } )

          // tmp_holder.time.push(Math.round(element.time/ 1000000)) // we receive time in microseconds
          tmp_holder.time.push(this.roundMultiple(element.time, multiple_to_use)) // we receive time in microseconds
          tmp_holder.cpu.push(element.cpu) // we receive time in microseconds
          tmp_holder.mem.push(element.mem) // we receive time in microseconds
          tmp_holder.rx_bytes.push(element.rx_bytes) // we receive time in microseconds
          tmp_holder.rx_packets.push(element.rx_packets) // we receive time in microseconds
          tmp_holder.rx_dropped.push(element.rx_dropped) // we receive time in microseconds
          tmp_holder.tx_bytes.push(element.tx_bytes) // we receive time in microseconds
          tmp_holder.tx_packets.push(element.tx_packets) // we receive time in microseconds
          tmp_holder.tx_dropped.push(element.tx_dropped) // we receive time in microseconds

          // tmp_holder.netOut.push(element.netOut / division_factor )        // bytes
          // tmp_holder.diskRead.push(element.diskRead / division_factor )    // bytes
          // tmp_holder.diskWrite.push(element.diskWrite / division_factor )  // bytes

          // save to holder
          stats[container_id] = tmp_holder
      }
      this.setState({containers_data: stats})
  }


  toggle_code() {
    this.setState({hide_code: !this.state.hide_code})
  }

  render_plots(ctx) {
    // data={Object.keys(ctx.state.hosts_data).map((hostname, index) => {
    //   return {
    //     x: ctx.state.hosts_data[hostname].time,
    //     y: ctx.state.hosts_data[hostname][element],
    //     type: 'scatter',
    //     name: hostname
    //   }})}
    console.log()
    return ([
              ["cpu", "CPU Usage", "Load Average"],
              ["mem", "Memory Usage", "Bytes"],
              ["rx_bytes", "Bytes Received", "Bytes"],
              ["tx_bytes", "Bytes Sent", "Bytes"],
              ["rx_packets", "Number Incoming Packets", ""],
              ["rx_dropped", "Number Dropped Incoming Packets", ""],
              ["tx_packets", "Number Outgoing Packets", ""],
              ["tx_dropped", "Number Dropped Outgoing Packets", ""],
            ]).map((element) =>
                <Row>
                      <Plot key={element[0]}
                          data={
                            Object.keys(ctx.state.containers_data).map((container_id) => {
                            return {
                                x: ctx.state.containers_data[container_id].time,
                                y: ctx.state.containers_data[container_id][element[0]],
                                type: 'scatter',
                                name: ctx.state.containers[container_id.substring(0, NUMBER_LETTERS)].service + ":" + ctx.state.containers[container_id.substring(0, NUMBER_LETTERS)].slot,
                                visible: !ctx.state.containers[container_id.substring(0, NUMBER_LETTERS)].disabled,
                                transforms: [{
                                    type: 'aggregate',
                                    groups: ctx.state.containers_data[container_id].time,
                                    aggregations: [
                                      {target: 'y', func: 'avg', enabled: true},
                                    ]
                                }]

                            }})
                          }
                          layout={{
                                xaxis: {
                                  title: "Time [s]",
                                  rangemode: "tozero",
                                  titlefont: {
                                    family: "Courier New, monospace",
                                    size: 18,
                                    // color: "#7f7f7f"
                                  },
                                },
                                yaxis: {
                                  tickformat: "s",
                                  rangemode: "tozero",
                                  title: element[2],
                                  titlefont: {
                                    family: "Courier New, monospace",
                                    size: 18,
                                    // color: "#7f7f7f"
                                  },
                                },
                                width: ctx.state.width-300,
                                height: ctx.state.graphs_height,

                                // title:element[1]
                              }}
                          config={ctx.state.config}
                      />
                </Row>
  )

    // {Object.keys(this.state.hosts_data).map((key, index) =>
    //
    //
    //       <Col key={index} md={4}>
    //           <ToggleButton key={index} container_id={key} service={this.state.containers[key].service} slot={this.state.containers[key].slot} handleClick={() => this.handleClick(key)} disabled={this.state.containers[key].disabled} ></ToggleButton>
    //       </Col>
    //     )
    // }

  }

  updateMultipleValue(evt){
    this.load_containers_data(parseInt(evt.target.value))
  }

  render() {

    return (
      <div className="content">
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
              <input type="text" id="addpixinputfield" onChange={this.updateMultipleValue.bind(this)}/>
          </Row>
          {this.render_plots(this)}
          <Row>
            <button onClick={this.toggle_code.bind(this)} > {this.state.hide_code ? "Show" : "Hide"} Filters </button>
            <div id="demo" className={"collapse" + (this.state.hide_code ? '' : ' in')}>
              <pre>
                 <code>
                   {JSON.stringify(this.state.containers_data,
                     null,
                     2
                   )}
                 </code>
               </pre>
             </div>
          </Row>
        </Grid>
      </div>
    );
  }
}
// class Graph extends Component {
//   render() {
//     return <p> Hello World</p>
//   }
// }

export default GraphContainers;
