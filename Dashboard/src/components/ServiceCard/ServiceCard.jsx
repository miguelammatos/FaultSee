import React, { Component } from "react";
import { Grid, Row, Col } from "react-bootstrap";
import ToggleButton from 'components/ToggleButton/ToggleButton'
import Card from "components/Card/Card";
import ContainerCard from "components/ContainerCard/ContainerCard";

class ServiceCard extends Component {3

    render() {
        return <Card
            title={this.props.service}
            // category={this.props.container_id.substring(0, this.props.number_letters)}
            content={
              <Grid>
                  <Row>
                      <Col md={3} mdOffset={1}>
                          <button onClick={this.props.only_this_service_click}>Display Only This Service</button>
                      </Col>
                      <Col md={3} mdOffset={1}>
                          <button onClick={this.props.hide_all_containers_click}>Hide All Containers</button>
                      </Col>
                      <Col md={3} mdOffset={1}>
                          <button onClick={this.props.show_all_containers_click}>Show All Containers</button>
                      </Col>

                  </Row>
                  <Row style={{ marginTop: 30 }}> </Row >

                  <Row>
                      {Object.keys(this.props.containers).map((container_id, index) =>
                          // filter service
                          this.props.containers[container_id].service == this.props.service
                          ?
                                  <Col key={container_id} md={3} mdOffset={2}>

                                      <ContainerCard
                                            container_id={container_id}
                                            service={this.props.containers[container_id].service}
                                            slot={this.props.containers[container_id].slot}
                                            handle_click_only_this={() => this.props.handle_click_only_this_container(container_id)}
                                            handle_click_simple_toggle={() => this.props.handle_click_toggle_container(container_id)}
                                            disabled_simple_toggle={this.props.containers[container_id].disabled}
                                             />
                                  </Col>
                          :
                                  null
                        )}
                        <Col md={1}/>
                    </Row>
                </Grid>

              }
            />

    }

}

//  ---- Props ----
// service

// only_this_service_click
// hide_all_containers_click
// show_all_containers_click

// containers

// handle_click_toggle_container
// handle_click_only_this_container


export default ServiceCard
