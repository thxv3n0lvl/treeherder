import React from 'react';
import PropTypes from 'prop-types';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faRedo } from '@fortawesome/free-solid-svg-icons';
import {
  faPlusSquare,
  faMinusSquare,
} from '@fortawesome/free-regular-svg-icons';
import {
  Row,
  Collapse,
  Badge,
  ButtonGroup,
  ButtonDropdown,
  Button,
  DropdownMenu,
  DropdownToggle,
  DropdownItem,
  Navbar,
  Nav,
  NavItem,
  UncontrolledButtonDropdown,
} from 'reactstrap';

import JobModel from '../models/job';

import TestFailure from './TestFailure';

class ClassificationGroup extends React.PureComponent {
  constructor(props) {
    super(props);

    this.state = {
      detailsShowing: props.expanded,
      retriggerDropdownOpen: false,
      groupedBy: 'none',
    };
  }

  toggleDetails = () => {
    this.setState(prevState => ({ detailsShowing: !prevState.detailsShowing }));
  };

  toggleRetrigger = () => {
    this.setState(prevState => ({
      retriggerDropdownOpen: !prevState.retriggerDropdownOpen,
    }));
  };

  retriggerAll = times => {
    const { group, notify, currentRepo } = this.props;
    // Reduce down to the unique jobs
    const jobs = group.reduce(
      (acc, test) => ({
        ...acc,
        ...test.failJobs.reduce((fjAcc, fJob) => ({ [fJob.id]: fJob }), {}),
      }),
      {},
    );
    const uniqueJobs = Object.values(jobs);

    JobModel.retrigger(uniqueJobs, currentRepo, notify, times);
  };

  setGroupedBy = groupedBy => {
    this.setState({ groupedBy });
  };

  getGroupedTests = group => {
    const { groupedBy } = this.state;
    console.log('group', group);
    // return group;
    if (groupedBy === 'none') {
      return { none: group };
    }
    if (groupedBy === 'path') {
      return group.reduce(
        (acc, test) => ({
          ...acc,
          [test.testName]: acc[test.testName]
            ? [...acc[test.testName], test]
            : [test],
        }),
        {},
      );
    }
    if (groupedBy === 'platform') {
      return group.reduce(
        (acc, test) => ({
          ...acc,
          [`${test.platform} ${test.config}`]: acc[
            `${test.platform} ${test.config}`
          ]
            ? [...acc[`${test.platform} ${test.config}`], test]
            : [test],
        }),
        {},
      );
    }
  };

  render() {
    const { detailsShowing, retriggerDropdownOpen, groupedBy } = this.state;
    const {
      group,
      name,
      repo,
      revision,
      className,
      headerColor,
      user,
      hasRetriggerAll,
      notify,
      currentRepo,
    } = this.props;
    const expandIcon = detailsShowing ? faMinusSquare : faPlusSquare;
    const expandTitle = detailsShowing
      ? 'Click to collapse'
      : 'Click to expand';
    const groupedTests = this.getGroupedTests(group);
    console.log('grouped', groupedTests);

    return (
      <Row className={`justify-content-between ${className}`}>
        <h4 className="w-100">
          <Badge
            className="pointable w-100"
            onClick={this.toggleDetails}
            color={headerColor}
            role="button"
            aria-expanded={detailsShowing}
          >
            {name} : {Object.keys(group).length}
            <FontAwesomeIcon
              icon={expandIcon}
              className="ml-1"
              title={expandTitle}
              aria-label={expandTitle}
            />
          </Badge>
        </h4>
        <Collapse isOpen={detailsShowing} className="w-100">
          {hasRetriggerAll && (
            <Navbar>
              <Nav>
                <NavItem>
                  <ButtonGroup size="sm">
                    <Button
                      title="Retrigger all 'Need Investigation' jobs once"
                      onClick={() => this.retriggerAll(1)}
                      size="sm"
                    >
                      <FontAwesomeIcon
                        icon={faRedo}
                        title="Retrigger"
                        className="mr-2"
                      />
                      Retrigger all
                    </Button>
                    <ButtonDropdown
                      isOpen={retriggerDropdownOpen}
                      toggle={this.toggleRetrigger}
                      size="sm"
                    >
                      <DropdownToggle caret />
                      <DropdownMenu>
                        {[5, 10, 15].map(times => (
                          <DropdownItem
                            key={times}
                            title={`Retrigger all 'Need Investigation' jobs ${times} times`}
                            onClick={() => this.retriggerAll(times)}
                          >
                            Retrigger all {times} times
                          </DropdownItem>
                        ))}
                      </DropdownMenu>
                    </ButtonDropdown>
                  </ButtonGroup>
                </NavItem>
                <NavItem>
                  <UncontrolledButtonDropdown size="sm" className="ml-1">
                    <DropdownToggle
                      className="btn-sm ml-1 text-capitalize"
                      id="groupTestsDropdown"
                      caret
                    >
                      Group By: {groupedBy}
                    </DropdownToggle>
                    <DropdownMenu toggler="groupTestsDropdown">
                      <DropdownItem
                        className="btn-sm ml-1"
                        onClick={() => this.setGroupedBy('none')}
                      >
                        None
                      </DropdownItem>
                      <DropdownItem
                        className="btn-sm ml-1"
                        onClick={() => this.setGroupedBy('path')}
                      >
                        Test path
                      </DropdownItem>
                      <DropdownItem
                        className="btn-sm ml-1"
                        onClick={() => this.setGroupedBy('platform')}
                      >
                        Platform
                      </DropdownItem>
                    </DropdownMenu>
                  </UncontrolledButtonDropdown>
                </NavItem>
              </Nav>
            </Navbar>
          )}
          <div>
            {groupedTests &&
              Object.entries(groupedTests).map(([key, tests]) => (
                <div>
                  {key !== 'none' && (
                    <div className="h5 mt-3 border-bottom border-secondary">
                      {key}
                    </div>
                  )}
                  {tests.map(failure => (
                    <TestFailure
                      key={failure.key}
                      failure={failure}
                      repo={repo}
                      currentRepo={currentRepo}
                      revision={revision}
                      user={user}
                      notify={notify}
                      groupedBy={groupedBy}
                      className="ml-3"
                    />
                  ))}
                </div>
              ))}
          </div>
        </Collapse>
      </Row>
    );
  }
}

ClassificationGroup.propTypes = {
  group: PropTypes.array.isRequired,
  name: PropTypes.string.isRequired,
  repo: PropTypes.string.isRequired,
  currentRepo: PropTypes.object.isRequired,
  revision: PropTypes.string.isRequired,
  user: PropTypes.object.isRequired,
  notify: PropTypes.func.isRequired,
  hasRetriggerAll: PropTypes.bool,
  expanded: PropTypes.bool,
  className: PropTypes.string,
  headerColor: PropTypes.string,
};

ClassificationGroup.defaultProps = {
  expanded: true,
  className: '',
  headerColor: '',
  hasRetriggerAll: false,
};

export default ClassificationGroup;
