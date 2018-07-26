import React, { Component } from "react";
import { Table, Grid, Row, Col, Dropdown } from "react-bootstrap";

import Card from "components/Card/Card";

import Button from "components/CustomButton/CustomButton";

import Plot from 'react-plotly.js';

import * as array_events_json from "variables/containers_events.json"
import * as array_marks_json from "variables/marks.json"

const array_events = array_events_json.default
const array_marks = array_marks_json.default

class GraphInstances extends Component {
  constructor(props) {
      super(props);
      this.state = {
            width: 0,
            graphs_height: 400,
            timelines: {},
            containers_data: {},
            multiple: 5,
            shapes: [],
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
    this.updateDimensions();
    // this.setState({ containers: Load_Containers_IDS() });
    this.loadContainerEvents()
    this.get_shapes()
    window.addEventListener("resize", this.updateDimensions.bind(this));
  }
  updateDimensions() {
    this.setState({ width: window.innerWidth });
  }

  loadContainerEvents() {
      var timelines = {}
      var timelines_min_y = 0
      var timelines_max_y = 0
      // NOTE: Assuiming time sorted!!!
      for (var index = 0; index < array_events.length; ++index) {
          var element = array_events[index]
          var service = element.service
          var time = element.time
          var action = element.action

          var tmp_holder = (timelines[service] || {x: [], y: []} )


          var prev_y = tmp_holder.y[tmp_holder.y.length - 1] || 0
          let new_y
          if (action == "start" ) {
              new_y = prev_y + 1
          } else if (action == "die") {
              new_y = prev_y - 1
          } else {
              //TODO
              console.log(action)
          }
          tmp_holder.x.push(time)
          tmp_holder.y.push(prev_y)

          tmp_holder.x.push(time)
          tmp_holder.y.push(new_y)

          if (new_y > timelines_max_y) {
              timelines_max_y = new_y
          } else if (new_y < timelines_min_y) {
              timelines_min_y = new_y
          }


          timelines[service] = tmp_holder

      }
      this.setState({timelines: timelines,
                     timelines_max_y: (timelines_max_y+1),
                     timelines_min_y: (timelines_min_y-1),
      })
  }

  roundMultiple(x, multiple)
  {
      return (x % multiple) >= (multiple/2) ? parseInt(x / multiple) * multiple + multiple : parseInt(x / multiple) * multiple;
  }




  toggle_code() {
    this.setState({hide_code: !this.state.hide_code})
  }

  get_shapes() {
      // {"time": 0.0, "hostname": "faultsee-1", "msg": "start"}
      var shapes = []
      for (var index = 0; index < array_marks.length; ++index) {
        var element = array_marks[index]
        shapes.push( element.time )
      }
      this.setState({shapes: shapes})
  }

  render_plots(ctx) {
    return (
                <Row>
                      <Plot
                          data={
                            Object.keys(ctx.state.timelines).map((service) => {
                            return {
                                x: ctx.state.timelines[service].x,
                                y: ctx.state.timelines[service].y,
                                hoverinfo: 'x+y+name',
                                mode: 'lines',
                                name: service,
                                visible: true,
                                //
                                // transforms: [{
                                //     type: 'aggregate',
                                //     groups: ctx.state.containers_data[container_id].time,
                                //     aggregations: [
                                //       {target: 'y', func: 'avg', enabled: true},
                                //     ]
                                // }]
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
                                  rangemode: "tozero",
                                  tickformat: "d",
                                  title: "Number Containers",
                                  titlefont: {
                                    family: "Courier New, monospace",
                                    size: 18,
                                    // color: "#7f7f7f"
                                  },
                                },
                                width: ctx.state.width-300,
                                height: ctx.state.graphs_height,
                                shapes: ctx.state.shapes.map((element_time) => {
                                    return {
                                      type: 'line',
                                      x0: element_time,
                                      y0: ctx.state.timelines_min_y,
                                      x1: element_time,
                                      y1: ctx.state.timelines_max_y,
                                      line: {
                                        color: 'rgb(220,220,220)',
                                        width: 1,
                                        dash: 'dashdot',

                                      }
                                    }
                                }),
                                // title:"Instances"
                              }}
                          config={ctx.state.config}
                      />
                </Row>
              )

      }


    // {Object.keys(this.state.hosts_data).map((key, index) =>
    //
    //
    //       <Col key={index} md={4}>
    //           <ToggleButton key={index} container_id={key} service={this.state.containers[key].service} slot={this.state.containers[key].slot} handleClick={() => this.handleClick(key)} disabled={this.state.containers[key].disabled} ></ToggleButton>
    //       </Col>
    //     )
    // }

  updateMultipleValue(evt){

    console.log("input field updated with "+parseInt(evt.target.value));
    this.setState({ multiple: parseInt(evt.target.value) })
    this.loadYCSB(parseInt(evt.target.value))
  }

  render() {

    return (
      <div className="content">
        <Grid fluid>
          {this.render_plots(this)}
          <Row>
              <input type="text" id="addpixinputfield" onChange={this.updateMultipleValue.bind(this)}/>
          </Row>

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

export default GraphInstances;
