import React, { Component } from "react";
import { Table, Grid, Row, Col } from "react-bootstrap";

import Card from "components/Card/Card";

import Button from "components/CustomButton/CustomButton";

import Plot from 'react-plotly.js';

import * as array_stats_json from "variables/host_stats.json"

const array_stats = array_stats_json.default

class Graph extends Component {
  constructor(props) {
      super(props);
      this.state = {
            width: 10,
            graphs_height: 400,
            hosts_data: {},
            frames: [],
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
    this.load_host_data(1)
    this.updateDimensions();
    window.addEventListener("resize", this.updateDimensions.bind(this));
  }
  updateDimensions() {
    this.setState({ width: window.innerWidth });
    this.render()
  }
  updateMultipleValue(evt){
    this.load_host_data(parseInt(evt.target.value))
  }


  roundMultiple(x, multiple)
  {
      return (x % multiple) >= (multiple/2) ? parseInt(x / multiple) * multiple + multiple : parseInt(x / multiple) * multiple;
  }

  load_host_data(multiple_to_use) {
      var stats = {}
      // var data_template =
      const previous_calculator_helper = [
          { previous: "prevNetIn",
               array: "netIn"},
          { previous: "prevNetOut",
               array: "netOut"},
          {  previous: "prevDiskRead",
                array: "diskRead"},
          {  previous: "prevDiskWrite",
                array: "diskWrite"},
      ]

      const calculate_based_on_prev = false

      // NOTE: Assuiming time sorted!!!
      for (var index = 0; index < array_stats.length; ++index) {
          var element = array_stats[index]
          var hostname = element.hostname
          console.log(hostname)

          // get holder
          var tmp_holder = (stats[hostname] || {
              time: [],
              cpu: [],
              dummy: [],
              mem: [],
              netIn: [],
              netOut: [],
              diskRead: [],
              diskWrite: [],
          } )

          // tmp_holder.time.push(Math.round(element.time/ 1000000)) // we receive time in microseconds
          // tmp_holder.time.push(element.time) // we receive time in microseconds
          tmp_holder.time.push(this.roundMultiple(element.time, multiple_to_use)) // we receive time in microseconds
          tmp_holder.cpu.push(element.cpu)
          tmp_holder.mem.push(element.mem)
          tmp_holder.netIn.push(element.netIn )        // bytes
          tmp_holder.netOut.push(element.netOut )        // bytes
          tmp_holder.diskRead.push(element.diskRead )    // bytes
          tmp_holder.diskWrite.push(element.diskWrite )  // bytes

          // save to holder
          stats[hostname] = tmp_holder
      }
      this.setState({hosts_data: stats})
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
            ["cpu", "CPU usage", "Percentage"],
            ["mem", "Memory Usage", "Percentage"],
            ["netIn", "Incoming Network", "Bytes"],
            ["netOut", "Outgoing Network", "Bytes"],
            ["diskRead", "Disk Read", "Bytes"],
            ["diskWrite", "Disk Write", "Bytes"],
          ]).map((element) =>
                <Row>
                  <Card
                    title={element[1]}
                    // category="Backend development"
                    content={
                        <Plot key={element[0]}
                            data={
                              Object.keys(ctx.state.hosts_data).map((hostname) => {
                                console.log(hostname)
                              return {
                                  x: ctx.state.hosts_data[hostname].time,
                                  y: ctx.state.hosts_data[hostname][element[0]],
                                  type: 'scatter',
                                  name: hostname,
                                  visible: true,

                                  transforms: [{
                                      type: 'aggregate',
                                      groups: ctx.state.hosts_data[hostname].time,
                                      aggregations: [
                                        {target: 'y', func: 'avg', enabled: true},
                                      ]
                                  }]

                              }})
                              }
                            layout={
                              {
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
                            margin= {{
                                t: 20, //top margin
                                l: 20, //left margin
                                r: 20, //right margin
                                b: 20 //bottom margin
                            }}
                            config={ctx.state.config}

                          />
                  }/>


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

  render() {
    return (


      <div className="content">
        <Grid fluid>
          <Row>
              <input type="text" id="addpixinputfield" onChange={this.updateMultipleValue.bind(this)}/>
          </Row>

          {this.render_plots(this)}
          <Row>
            <button onClick={this.toggle_code.bind(this)} > {this.state.hide_code ? "Show" : "Hide"} Filters </button>
            <div id="demo" className={"collapse" + (this.state.hide_code ? '' : ' in')}>
              <pre>
                 <code>
                   {JSON.stringify(this.state.hosts_data,
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

export default Graph;
