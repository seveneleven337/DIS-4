"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import {
  RecordCreate,
  RecordData,
  RecordResponse,
  StorageLocation,
} from "@/types/record";

interface Props {
  open: boolean;
  record: RecordResponse | null;
  onClose: () => void;
  onSubmit: (record: RecordCreate, version?: number) => Promise<void>;
}

type FieldDefinition = {
  path: string;
  label: string;
  type?: "text" | "number" | "date" | "time";
  nullable?: boolean;
};

const fields: { title: string; items: FieldDefinition[] }[] = [
  {
    title: "Customer",
    items: [
      { path: "customer.customer_id", label: "Customer ID" },
      { path: "customer.customer_name", label: "Customer name" },
      { path: "customer.customer_gender", label: "Gender", nullable: true },
      { path: "customer.customer_segment", label: "Segment", nullable: true },
    ],
  },
  {
    title: "Store",
    items: [
      { path: "store.store_id", label: "Store ID" },
      { path: "store.store_name", label: "Store name" },
      { path: "store.country", label: "Country" },
      { path: "store.region", label: "Region", nullable: true },
      { path: "store.city", label: "City", nullable: true },
    ],
  },
  {
    title: "Sales representative",
    items: [
      {
        path: "sales_representative.sales_representative_id",
        label: "Representative ID",
        type: "number",
        nullable: true,
      },
      {
        path: "sales_representative.sales_representative_name",
        label: "Representative name",
      },
    ],
  },
  {
    title: "Product",
    items: [
      { path: "product.product_id", label: "Product ID" },
      { path: "product.product_name", label: "Product name" },
      { path: "product.product_category", label: "Category" },
      {
        path: "product.product_subcategory",
        label: "Subcategory",
        nullable: true,
      },
    ],
  },
  {
    title: "Promotion",
    items: [
      {
        path: "promotion.promotion_code",
        label: "Promotion code",
        nullable: true,
      },
    ],
  },
  {
    title: "Order",
    items: [
      { path: "order.order_id", label: "Order ID" },
      { path: "order.customer_id", label: "Order customer ID" },
      { path: "order.store_id", label: "Order store ID" },
      {
        path: "order.sales_representative_id",
        label: "Order representative ID",
        type: "number",
      },
      {
        path: "order.promotion_code",
        label: "Order promotion code",
        nullable: true,
      },
      { path: "order.order_date", label: "Order date", type: "date" },
      { path: "order.order_time", label: "Order time", type: "time" },
      { path: "order.sales_channel", label: "Sales channel" },
      { path: "order.payment_method", label: "Payment method" },
      { path: "order.order_status", label: "Order status" },
      { path: "order.shipping_method", label: "Shipping method" },
      {
        path: "order.delivery_days",
        label: "Delivery days",
        type: "number",
        nullable: true,
      },
      {
        path: "order.customer_rating",
        label: "Customer rating",
        type: "number",
        nullable: true,
      },
    ],
  },
  {
    title: "Transaction",
    items: [
      { path: "transaction.transaction_id", label: "Transaction ID" },
      { path: "transaction.order_id", label: "Transaction order ID" },
      { path: "transaction.product_id", label: "Transaction product ID" },
      {
        path: "transaction.customer_age",
        label: "Customer age",
        type: "number",
        nullable: true,
      },
      { path: "transaction.quantity", label: "Quantity", type: "number" },
      { path: "transaction.unit_price", label: "Unit price", type: "number" },
      {
        path: "transaction.discount_percentage",
        label: "Discount percentage",
        type: "number",
      },
      {
        path: "transaction.sales_amount",
        label: "Sales amount",
        type: "number",
      },
      {
        path: "transaction.cost_amount",
        label: "Cost amount",
        type: "number",
      },
      {
        path: "transaction.profit",
        label: "Profit",
        type: "number",
        nullable: true,
      },
      {
        path: "transaction.inventory_level",
        label: "Inventory level",
        type: "number",
        nullable: true,
      },
    ],
  },
  {
    title: "Return",
    items: [
      {
        path: "return_record.return_reason",
        label: "Return reason",
        nullable: true,
      },
    ],
  },
];

const immutablePaths = new Set([
  "customer.customer_id",
  "store.store_id",
  "sales_representative.sales_representative_id",
  "product.product_id",
  "promotion.promotion_code",
  "order.order_id",
  "order.customer_id",
  "order.store_id",
  "order.sales_representative_id",
  "order.promotion_code",
  "transaction.transaction_id",
  "transaction.order_id",
  "transaction.product_id",
]);

function emptyRecord(): RecordData {
  return {
    customer: {
      customer_id: "",
      customer_name: "",
      customer_gender: null,
      customer_segment: null,
    },
    store: {
      store_id: "",
      store_name: "",
      country: "",
      region: null,
      city: null,
    },
    sales_representative: {
      sales_representative_id: 1,
      sales_representative_name: "",
    },
    product: {
      product_id: "",
      product_name: "",
      product_category: "",
      product_subcategory: null,
    },
    promotion: null,
    order: {
      order_id: "",
      customer_id: "",
      store_id: "",
      sales_representative_id: 1,
      promotion_code: null,
      order_date: new Date().toISOString().slice(0, 10),
      order_time: "12:00",
      sales_channel: "",
      payment_method: "",
      order_status: "",
      shipping_method: "",
      delivery_days: null,
      customer_rating: null,
    },
    transaction: {
      transaction_id: "",
      order_id: "",
      product_id: "",
      customer_age: null,
      quantity: 1,
      unit_price: 0,
      discount_percentage: 0,
      sales_amount: 0,
      cost_amount: 0,
      profit: null,
      inventory_level: null,
    },
    return_record: null,
  };
}

function readPath(source: RecordData, path: string): unknown {
  return path.split(".").reduce<unknown>((current, key) => {
    if (current === null || typeof current !== "object") return undefined;
    return (current as Record<string, unknown>)[key];
  }, source);
}

function writePath(
  source: RecordData,
  path: string,
  value: unknown,
): RecordData {
  const result = structuredClone(source) as unknown as Record<
    string,
    unknown
  >;

  const parts = path.split(".");
  let current = result;

  for (let index = 0; index < parts.length - 1; index++) {
    const key = parts[index];

    if (current[key] === null || typeof current[key] !== "object") {
      current[key] = {};
    }

    current = current[key] as Record<string, unknown>;
  }

  current[parts[parts.length - 1]] = value;

  return result as unknown as RecordData;
}

function recordToData(record: RecordResponse): RecordData {
  return {
    customer: { ...record.customer },
    store: { ...record.store },
    sales_representative: { ...record.sales_representative },
    product: { ...record.product },
    promotion: record.promotion ? { ...record.promotion } : null,
    order: { ...record.order },
    transaction: { ...record.transaction },
    return_record: record.return_record
      ? { ...record.return_record }
      : null,
  };
}

export default function RecordFormDialog({
  open,
  record,
  onClose,
  onSubmit,
}: Props) {
  const [form, setForm] = useState<RecordData>(emptyRecord);
  const [storageLocation, setStorageLocation] =
    useState<StorageLocation>("POSTGRESQL");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;

    setForm(record ? recordToData(record) : emptyRecord());
    setStorageLocation(record?.storage_location ?? "POSTGRESQL");
    setError("");
  }, [open, record]);

  function updateField(path: string, rawValue: string, type = "text") {
    let value: unknown = rawValue;

    if (type === "number") {
      value = rawValue === "" ? null : Number(rawValue);
    } else if (
      rawValue === "" &&
      fields.some((section) =>
        section.items.some(
          (item) => item.path === path && item.nullable,
        ),
      )
    ) {
      value = null;
    }

    setForm((previous) => {
      let next = writePath(previous, path, value);

      if (path === "order.order_id") {
        next = writePath(next, "transaction.order_id", value);

        if (next.return_record) {
          next = writePath(next, "return_record.order_id", value);
        }
      }

      if (path === "order.customer_id") {
        next = writePath(next, "customer.customer_id", value);
      }

      if (path === "order.store_id") {
        next = writePath(next, "store.store_id", value);
      }

      if (path === "order.sales_representative_id") {
        next = writePath(
          next,
          "sales_representative.sales_representative_id",
          value,
        );
      }

      if (path === "order.promotion_code") {
        next = writePath(
          next,
          "promotion.promotion_code",
          value || null,
        );
      }

      return next;
    });
  }

  function toggleOptionalSection(section: "promotion" | "return_record") {
    setForm((previous) => {
      if (previous[section]) {
        return { ...previous, [section]: null };
      }

      if (section === "promotion") {
        return {
          ...previous,
          promotion: { promotion_code: "" },
        };
      }

      return {
        ...previous,
        return_record: {
          order_id: previous.order.order_id,
          return_reason: null,
        },
      };
    });
  }

  async function handleSubmit() {
    setError("");

    const normalized: RecordData = {
      ...form,
      order: {
        ...form.order,
        customer_id: form.customer.customer_id,
        store_id: form.store.store_id,
        sales_representative_id:
          form.sales_representative.sales_representative_id ?? 1,
        promotion_code: form.promotion?.promotion_code || null,
      },
      transaction: {
        ...form.transaction,
        order_id: form.order.order_id,
        product_id: form.product.product_id,
      },
      return_record: form.return_record
        ? {
            ...form.return_record,
            order_id: form.order.order_id,
          }
        : null,
    };

    if (!normalized.order.order_id.trim()) {
      setError("Order ID is required.");
      return;
    }

    if (!normalized.transaction.transaction_id.trim()) {
      setError("Transaction ID is required.");
      return;
    }

    if (
      normalized.promotion &&
      !normalized.promotion.promotion_code.trim()
    ) {
      setError("Promotion code cannot be empty. Disable the promotion instead.");
      return;
    }

    setSaving(true);

    try {
      await onSubmit(
        {
          ...normalized,
          storage_location: record?.storage_location ?? storageLocation,
        },
        record?.version,
      );

      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save the record.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={saving ? undefined : onClose}
      fullWidth
      maxWidth="lg"
    >
      <DialogTitle>
        {record ? "Edit record" : "Create record"}
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={3} sx={{ pt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}

          {!record && (
            <FormControl fullWidth>
              <InputLabel id="storage-location-label">
                Storage location
              </InputLabel>

              <Select
                labelId="storage-location-label"
                label="Storage location"
                value={storageLocation}
                onChange={(event) =>
                  setStorageLocation(
                    event.target.value as StorageLocation,
                  )
                }
              >
                <MenuItem value="POSTGRESQL">PostgreSQL</MenuItem>
                <MenuItem value="MONGODB">MongoDB</MenuItem>
                <MenuItem value="BOTH">Both databases</MenuItem>
              </Select>
            </FormControl>
          )}

          {record ? (
            <Alert severity="info">
              Storage location: <strong>{record.storage_location}</strong>.
              Storage location and entity identifiers cannot be changed
              when editing a record.
            </Alert>
          ) : (
            <Alert severity="info">
              Related identifiers are synchronized automatically when their
              corresponding order fields are changed.
            </Alert>
          )}

          {fields.map((section) => (
            <Box key={section.title}>
              <Stack
                direction="row"
                sx={{
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 1.5,
                }}
              >
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {section.title}
                </Typography>

                {section.title === "Return" && (
                  <Button
                    size="small"
                    onClick={() =>
                      toggleOptionalSection("return_record")
                    }
                  >
                    {form.return_record ? "Remove" : "Add return"}
                  </Button>
                )}

                {section.title === "Promotion" && !record && (
                  <Button
                    size="small"
                    onClick={() =>
                      toggleOptionalSection("promotion")
                    }
                  >
                    {form.promotion ? "Remove" : "Add promotion"}
                  </Button>
                )}
              </Stack>

              {section.title === "Promotion" && !form.promotion && (
                <Alert severity="info">
                  No promotion attached.
                </Alert>
              )}

              {section.title === "Return" && !form.return_record && (
                <Alert severity="info">
                  No return information.
                </Alert>
              )}

              {record &&
                section.title === "Promotion" &&
                form.promotion && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Promotion codes cannot be changed when editing a record.
                  </Alert>
                )}

              <Grid container spacing={2}>
                {section.items.map((field) => {
                  const optionalSection =
                    field.path.startsWith("promotion.") ||
                    field.path.startsWith("return_record.");

                  if (
                    optionalSection &&
                    (
                      (field.path.startsWith("promotion.") &&
                        !form.promotion) ||
                      (field.path.startsWith("return_record.") &&
                        !form.return_record)
                    )
                  ) {
                    return null;
                  }

                  const currentValue = readPath(form, field.path);
                  const immutable =
                    Boolean(record) && immutablePaths.has(field.path);

                  return (
                    <Grid
                      key={field.path}
                      size={{ xs: 12, sm: 6, md: 4 }}
                    >
                      <TextField
                        fullWidth
                        size="small"
                        label={field.label}
                        type={field.type ?? "text"}
                        value={
                          currentValue === null ||
                          currentValue === undefined
                            ? ""
                            : currentValue
                        }
                        disabled={immutable}
                        onChange={(event) =>
                          updateField(
                            field.path,
                            event.target.value,
                            field.type,
                          )
                        }
                        slotProps={{
                          htmlInput: {
                            step:
                              field.type === "number"
                                ? "any"
                                : undefined,
                          },
                        }}
                        helperText={
                          immutable
                            ? "Immutable identifier"
                            : field.nullable
                              ? "Optional"
                              : undefined
                        }
                      />
                    </Grid>
                  );
                })}
              </Grid>
            </Box>
          ))}
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button
          onClick={onClose}
          disabled={saving}
          color="inherit"
        >
          Cancel
        </Button>

        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={saving}
        >
          {saving
            ? "Saving..."
            : record
              ? "Save changes"
              : "Create record"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}