import React, { Component } from "react";

import { Button } from "react-bootstrap";


class ToggleButton extends Component {
  constructor(props) {
      super(props);
  }
    // getInitialState: function() {
    //   return {
    //     bgColor: 'red'
    //   }
    //
    // },



    render() {
      // var to_display = this.props.service + " : " +this.props.slot + " (" +this.props.container_id.substring(0, this.props.number_letters) + ")"

      return (
          <Button
            size="lg"
            bsStyle={!this.props.disabled ? "primary" : "danger" }
            bsClass='btn'
            // disabled={this.state.disabled}
            // style={backgroundColor: {this.state.bgColor}}
            // active={!this.props.disabled}
            onClick={this.props.handleClick}

            >{this.props.display} - {this.props.disabled ? "Dis" : "Act"}</Button>
      )
    }


}

export default ToggleButton;
