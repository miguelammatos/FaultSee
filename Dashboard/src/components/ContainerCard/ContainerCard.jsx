import React, { Component } from "react";
import { Grid, Row, Col } from "react-bootstrap";
import ToggleButton from 'components/ToggleButton/ToggleButton'
import Card from "components/Card/Card";

class ContainerCard extends Component {
  render() {
    var title = this.props.service + " : " +this.props.slot

    return <Card
        title={title}
        category={this.props.container_id.substring(0, this.props.number_letters)}
        content={
          <Row>
              <Col md={4}>
                  <button onClick={this.props.handle_click_only_this}>
                      only this container
                  </button>
              </Col>
              <Col md={4} mdOffset={1}>
                    <ToggleButton
                          display={this.props.disabled_simple_toggle ? "Show" : "Hide" }
                          handleClick={this.props.handle_click_simple_toggle}
                          disabled={this.props.disabled_simple_toggle}
                          />
              </Col>
              <Col md={1}><div/></Col>
          </Row>
        } />


  }

}

//  ---- Props ----
// handle_click_only_this
// handle_click_simple_toggle
// disabled_simple_toggle
// service
// slot
// container_id

export default ContainerCard
