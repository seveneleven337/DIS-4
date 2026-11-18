"use client";

import {
  Box,
  Chip,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { RecordResponse } from "@/types/record";

interface Props {
  records: RecordResponse[];
  onSelect: (record: RecordResponse) => void;
  onEdit: (record: RecordResponse) => void;
  onDelete: (record: RecordResponse) => void;
}

function StorageChip({ value }: { value: string }) {
  const color =
    value === "BOTH" ? "success" : value === "MONGODB" ? "secondary" : "primary";

  return (
    <Chip
      size="small"
      label={value === "BOTH" ? "Both" : value}
      color={color}
      variant="outlined"
    />
  );
}

export default function RecordsTable({
  records,
  onSelect,
  onEdit,
  onDelete,
}: Props) {
  if (records.length === 0) {
    return (
      <Paper sx={{ p: 5, textAlign: "center" }}>
        <Typography variant="h6">No records found</Typography>
        <Typography color="text.secondary" variant="body2">
          Try changing the filters or create a new record.
        </Typography>
      </Paper>
    );
  }

  return (
    <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Order ID</TableCell>
            <TableCell>Customer</TableCell>
            <TableCell>Product</TableCell>
            <TableCell>Order date</TableCell>
            <TableCell align="right">Sales amount</TableCell>
            <TableCell>Storage location</TableCell>
            <TableCell align="center">Status</TableCell>
            <TableCell align="center">Actions</TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {records.map((record) => (
            <TableRow
              key={record.order.order_id}
              hover
              onClick={() => onSelect(record)}
              sx={{ cursor: "pointer" }}
            >
              <TableCell>
                <Typography
                  variant="body2"
                  sx={{ fontWeight: 600 }}
                >
                  {record.order.order_id}
                </Typography>
              </TableCell>

              <TableCell>{record.customer.customer_name}</TableCell>
              <TableCell>{record.product.product_name}</TableCell>
              <TableCell>{record.order.order_date}</TableCell>

              <TableCell align="right">
                {record.transaction.sales_amount.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </TableCell>

              <TableCell>
                <StorageChip value={record.storage_location} />
              </TableCell>

              <TableCell align="center">
                <Chip
                  size="small"
                  label={record.order.order_status}
                  color={
                    record.order.order_status.toLowerCase() === "completed"
                      ? "success"
                      : "default"
                  }
                />
              </TableCell>

              <TableCell align="center">
                <Box
                  sx={{ display: "flex", justifyContent: "center" }}
                  onClick={(event) => event.stopPropagation()}
                >
                  <Tooltip title="Edit">
                    <IconButton
                      size="small"
                      onClick={() => onEdit(record)}
                      aria-label="Edit record"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>

                  <Tooltip title="Delete">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => onDelete(record)}
                      aria-label="Delete record"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
