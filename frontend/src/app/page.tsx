"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  InputAdornment,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import SearchIcon from "@mui/icons-material/Search";
import StorageIcon from "@mui/icons-material/Storage";
import RefreshIcon from "@mui/icons-material/Refresh";

import RecordsTable from "@/components/RecordsTable";
import RecordDetailsDialog from "@/components/RecordDetailsDialog";
import RecordFormDialog from "@/components/RecordFormDialog";

import {
  createRecord,
  deleteRecord,
  getRecords,
  updateRecord,
} from "@/lib/api";

import {
  RecordCreate,
  RecordResponse,
  RecordSource,
  RecordUpdate,
} from "@/types/record";

export default function Home() {
  const [records, setRecords] = useState<RecordResponse[]>([]);
  const [source, setSource] = useState<RecordSource>("ALL");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedRecord, setSelectedRecord] =
    useState<RecordResponse | null>(null);

  const [editingRecord, setEditingRecord] =
    useState<RecordResponse | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] =
    useState<RecordResponse | null>(null);

  const [notification, setNotification] = useState<{
    message: string;
    severity: "success" | "error";
  } | null>(null);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getRecords(source, search);
      setRecords(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Could not load records.";

      setError(message);
      setRecords([]);
    } finally {
      setLoading(false);
    }
  }, [source, search]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadRecords();
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [loadRecords]);

  const statistics = useMemo(
    () => ({
      total: records.length,
      postgres: records.filter(
        (record) =>
          record.storage_location === "POSTGRESQL" ||
          record.storage_location === "BOTH",
      ).length,
      mongo: records.filter(
        (record) =>
          record.storage_location === "MONGODB" ||
          record.storage_location === "BOTH",
      ).length,
      both: records.filter(
        (record) => record.storage_location === "BOTH",
      ).length,
    }),
    [records],
  );

  function openCreateDialog() {
    setEditingRecord(null);
    setFormOpen(true);
  }

  function openEditDialog(record: RecordResponse) {
    setEditingRecord(record);
    setFormOpen(true);
  }

  async function handleSave(data: RecordCreate, version?: number) {
    if (editingRecord) {
      if (version === undefined) {
        throw new Error("Missing record version.");
      }

      const update: RecordUpdate = {
        customer: data.customer,
        store: data.store,
        sales_representative: data.sales_representative,
        product: data.product,
        promotion: data.promotion,
        order: data.order,
        transaction: data.transaction,
        return_record: data.return_record,
        expected_version: version,
      };

      await updateRecord(editingRecord.order.order_id, update);

      setNotification({
        message: "Record updated successfully.",
        severity: "success",
      });
    } else {
      await createRecord(data);

      setNotification({
        message: "Record created successfully.",
        severity: "success",
      });
    }

    setFormOpen(false);
    setEditingRecord(null);
    await loadRecords();
  }

  async function handleDelete() {
    if (!deleteTarget) return;

    try {
      await deleteRecord(
        deleteTarget.order.order_id,
        deleteTarget.version,
      );

      setDeleteTarget(null);
      setNotification({
        message: "Record deleted successfully.",
        severity: "success",
      });

      await loadRecords();
    } catch (err) {
      setNotification({
        message:
          err instanceof Error ? err.message : "Could not delete record.",
        severity: "error",
      });
    }
  }

  const statCards = [
    {
      label: "Visible records",
      value: statistics.total,
      color: "primary.main",
    },
    {
      label: "In PostgreSQL",
      value: statistics.postgres,
      color: "info.main",
    },
    {
      label: "In MongoDB",
      value: statistics.mongo,
      color: "secondary.main",
    },
    {
      label: "Replicated in both",
      value: statistics.both,
      color: "success.main",
    },
  ];

  return (
    <Box sx={{ minHeight: "100vh", pb: 5 }}>
      <Box sx={{ bgcolor: "primary.dark", color: "white", py: 2, mb: 4 }}>
        <Container maxWidth="xl">
          <Stack
            direction="row"
            spacing={2}
            sx={{ alignItems: "center" }}
          >
            <StorageIcon fontSize="large" />
            <Box>
              <Typography variant="h5">
                Distributed Database Manager
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>
                PostgreSQL · MongoDB · Replication
              </Typography>
            </Box>
          </Stack>
        </Container>
      </Box>

      <Container maxWidth="xl">
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={2}
          sx={{
            justifyContent: "space-between",
            alignItems: { xs: "stretch", sm: "center" },
            mb: 3,
          }}
        >
          <Box>
            <Typography variant="h5" color="text.primary">
              Records
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage and monitor distributed records across databases.
            </Typography>
          </Box>

          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openCreateDialog}
          >
            Add record
          </Button>
        </Stack>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          {statCards.map((stat) => (
            <Grid key={stat.label} size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper sx={{ p: 2, height: "100%" }}>
                <Typography variant="body2" color="text.secondary">
                  {stat.label}
                </Typography>
                <Typography
                  variant="h4"
                  sx={{
                    fontWeight: 700,
                    color: stat.color,
                    mt: 0.5,
                  }}
                >
                  {stat.value}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>

        <Paper sx={{ p: 2, mb: 2 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            sx={{ alignItems: { xs: "stretch", md: "center" } }}
          >
            <TextField
              fullWidth
              size="small"
              placeholder="Search records..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                },
              }}
            />

            <FormControl size="small" sx={{ minWidth: 190 }}>
              <InputLabel id="source-filter-label">
                Database
              </InputLabel>
              <Select
                labelId="source-filter-label"
                label="Database"
                value={source}
                onChange={(event) =>
                  setSource(event.target.value as RecordSource)
                }
              >
                <MenuItem value="ALL">All databases</MenuItem>
                <MenuItem value="POSTGRESQL">PostgreSQL</MenuItem>
                <MenuItem value="MONGODB">MongoDB</MenuItem>
              </Select>
            </FormControl>

            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => void loadRecords()}
              disabled={loading}
            >
              Refresh
            </Button>
          </Stack>
        </Paper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Paper sx={{ p: 6, display: "flex", justifyContent: "center" }}>
            <CircularProgress />
          </Paper>
        ) : (
          <RecordsTable
            records={records}
            onSelect={setSelectedRecord}
            onEdit={openEditDialog}
            onDelete={setDeleteTarget}
          />
        )}

        <Stack
          direction="row"
          sx={{ justifyContent: "space-between", mt: 2 }}
        >
          <Typography variant="caption" color="text.secondary">
            Displaying {records.length} records (maximum 500).
          </Typography>

          <Chip
            size="small"
            variant="outlined"
            label={`Source: ${source}`}
          />
        </Stack>
      </Container>

      <RecordDetailsDialog
        open={Boolean(selectedRecord)}
        record={selectedRecord}
        onClose={() => setSelectedRecord(null)}
      />

      <RecordFormDialog
        open={formOpen}
        record={editingRecord}
        onClose={() => {
          setFormOpen(false);
          setEditingRecord(null);
        }}
        onSubmit={handleSave}
      />

      <Dialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
      >
        <DialogTitle>Delete record?</DialogTitle>
        <DialogContent>
          Are you sure you want to delete order{" "}
          <strong>{deleteTarget?.order.order_id}</strong>?
          This action cannot be undone.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} color="inherit">
            Cancel
          </Button>
          <Button onClick={() => void handleDelete()} color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(notification)}
        autoHideDuration={4000}
        onClose={() => setNotification(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        {notification ? (
          <Alert
            severity={notification.severity}
            onClose={() => setNotification(null)}
            variant="filled"
          >
            {notification.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Box>
  );
}
