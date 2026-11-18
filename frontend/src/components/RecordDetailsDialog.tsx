"use client";

import {
  Box,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { RecordResponse } from "@/types/record";

interface Props {
  open: boolean;
  record: RecordResponse | null;
  onClose: () => void;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (typeof value === "number") {
    return value.toLocaleString();
  }

  return String(value);
}

function EntitySection({
  title,
  data,
}: {
  title: string;
  data: object | null;
}) {
  if (!data) {
    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          {title}
        </Typography>
        <Typography color="text.secondary" variant="body2">
          No information available
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Typography
        variant="subtitle1"
        sx={{ fontWeight: 700, mb: 1.5 }}
      >
        {title}
      </Typography>

      <Grid container spacing={2}>
        {Object.entries(data).map(([key, value]) => (
          <Grid key={key} size={{ xs: 12, sm: 6, md: 4 }}>
            <Typography variant="caption" color="text.secondary">
              {key.replaceAll("_", " ")}
            </Typography>
            <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
              {formatValue(value)}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export default function RecordDetailsDialog({
  open,
  record,
  onClose,
}: Props) {
  if (!record) return null;

  const entities: {
    title: string;
    data: object | null;
  }[] = [
    { title: "Customer", data: record.customer },
    { title: "Store", data: record.store },
    {
      title: "Sales representative",
      data: record.sales_representative,
    },
    { title: "Product", data: record.product },
    { title: "Promotion", data: record.promotion },
    { title: "Order", data: record.order },
    { title: "Transaction", data: record.transaction },
    { title: "Return", data: record.return_record },
  ];

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>
        <Stack
          direction="row"
          sx={{
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Box>
            <Typography variant="h6">Order details</Typography>
            <Typography variant="body2" color="text.secondary">
              {record.order.order_id}
            </Typography>
          </Box>

          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Chip
              size="small"
              label={record.storage_location}
              color={
                record.storage_location === "BOTH" ? "success" : "primary"
              }
            />
            <IconButton onClick={onClose} aria-label="Close">
              <CloseIcon />
            </IconButton>
          </Stack>
        </Stack>
      </DialogTitle>

      <Divider />

      <DialogContent sx={{ pt: 3 }}>
        {entities.map((entity) => (
          <EntitySection
            key={entity.title}
            title={entity.title}
            data={entity.data}
          />
        ))}

        <Divider sx={{ my: 2 }} />

        <Typography variant="caption" color="text.secondary">
          Record version: {record.version}
        </Typography>
      </DialogContent>
    </Dialog>
  );
}
