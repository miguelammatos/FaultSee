import React, { Component } from "react";

import { Table } from "react-bootstrap";
import { useTable, useFilters } from 'react-table'


function FilterableTable({ columns, data }) {
  columns = React.useMemo(()=> columns, [])
  data = React.useMemo(()=> data, [])


  // const filterTypes = React.useMemo(
  //     () => ({ container_filter: container_filter }), [])

  // Use the state and functions returned from useTable to build your UI
  const { getTableProps, headerGroups, rows, prepareRow, state } = useTable({
      columns,
      data,
    },
    useFilters // useFilters!
  )
  state[0].filters = { "container_id": "" }


  // Render the UI for your table
  return (
    <div>

      <Table striped hover {...getTableProps()}>
        <thead>
          {headerGroups.map(headerGroup => (
            <tr {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map(column => (
                <th {...column.getHeaderProps()}>{column.render('Header')}</th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {rows.map(
            (row, i) =>
              prepareRow(row) || (
                <tr {...row.getRowProps()}>
                  {row.cells.map(cell => {
                    return <td {...cell.getCellProps()}>{cell.render('Cell')}</td>
                  })}
                </tr>
              )
          )}
        </tbody>
      </Table>
    </div>
  )
}


export default FilterableTable
