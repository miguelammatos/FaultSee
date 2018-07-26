import React, { Component } from "react";
import { Table, Grid, Row, Col } from "react-bootstrap";


import Card from "components/Card/Card";

import Button from "components/CustomButton/CustomButton";

import Plot from 'react-plotly.js';

import Containers_IDS from "utils/containers_ids"
import ServiceCard from 'components/ServiceCard/ServiceCard'


import * as array_stats_json from "variables/containers_stats.json"
import * as array_ids_json from "variables/containers_ids.json"

const array_stats = array_stats_json.default
const array_ids = array_ids_json.default

const NUMBER_LETTERS = 12


class AveragePlot extends Component {
  constructor(props) {
      super(props);
      this.state = {
            containers_data: {},
      };
  }

  // ------------------------------------------------
  //  toggles to control which containers to show
  // ------------------------------------------------



  render() {

    return (
      <div>
        <Plot key={this.props.key}
            data={
                  x: this.state.data.x,
                  y: this.state.data.y,
                  type: 'scatter',
                  name: this.props.name ,
                  visible: !this.props.visible
              }})
            }
            layout={{
                  xaxis: this.props.xaxis,
                  yaxis: this.props.yaxis,
                  width: this.props.width,
                  height: this.props.height,

                  title: this.props.title}}
            config={this.props.config}
        />
        <Row>
            <input type="text" id="addpixinputfield" onChange={this.updateMultipleValue.bind(this)}/>
        </Row>
      </div>
    );
  }
}
// class Graph extends Component {
//   render() {
//     return <p> Hello World</p>
//   }
// }

export default AveragePlot;
