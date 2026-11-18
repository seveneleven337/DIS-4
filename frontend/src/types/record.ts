export type StorageLocation = "POSTGRESQL" | "MONGODB" | "BOTH";

export interface Customer {
  customer_id: string;
  customer_name: string;
  customer_gender: string | null;
  customer_segment: string | null;
}

export interface Store {
  store_id: string;
  store_name: string;
  country: string;
  region: string | null;
  city: string | null;
}

export interface SalesRepresentative {
  sales_representative_id: number | null;
  sales_representative_name: string;
}

export interface Product {
  product_id: string;
  product_name: string;
  product_category: string;
  product_subcategory: string | null;
}

export interface Promotion {
  promotion_code: string;
}

export interface Order {
  order_id: string;
  customer_id: string;
  store_id: string;
  sales_representative_id: number;
  promotion_code: string | null;
  order_date: string;
  order_time: string;
  sales_channel: string;
  payment_method: string;
  order_status: string;
  shipping_method: string;
  delivery_days: number | null;
  customer_rating: number | null;
}

export interface Transaction {
  transaction_id: string;
  order_id: string;
  product_id: string;
  customer_age: number | null;
  quantity: number;
  unit_price: number;
  discount_percentage: number;
  sales_amount: number;
  cost_amount: number;
  profit: number | null;
  inventory_level: number | null;
}

export interface ReturnRecord {
  order_id: string;
  return_reason: string | null;
}

export interface RecordData {
  customer: Customer;
  store: Store;
  sales_representative: SalesRepresentative;
  product: Product;
  promotion: Promotion | null;
  order: Order;
  transaction: Transaction;
  return_record: ReturnRecord | null;
}

export interface RecordResponse extends RecordData {
  storage_location: StorageLocation;
  version: number;
}

export interface RecordCreate extends RecordData {
  storage_location: StorageLocation;
}

export interface RecordUpdate extends RecordData {
  expected_version: number;
}

export type RecordSource = "ALL" | "POSTGRESQL" | "MONGODB";