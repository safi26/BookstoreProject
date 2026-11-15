import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface ApiCategory {
  category_id: number;
  category_name: string;
  tax_exempt: boolean;
  student_discount_exempt: boolean;
  employee_discount_exempt: boolean;
  discount_type: 'none' | 'percent' | 'dollar';
  discount_value: string;
}

export interface ApiCourseSupplyBundle {
  id: number;
  name: string;
  items: number[];
}

export interface ApiItemVariant {
  variant_id: number;
  size: 'XS' | 'S' | 'M' | 'L' | 'XL' | 'XXL' | 'Unspecified';
  color: 'Blue' | 'Green' | 'Black' | 'Grey' | 'Red' | 'Unspecified';
  quantity: number;
}

export interface ApiItem {
  item_id: number;
  item: string;
  item_quantity: number;
  item_price: string;
  author: string;
  item_code: string;
  isbn: string;
  badge: string;
  category: number;
  category_name: string;
  cover_url: string;
  tax_exempt: boolean;
  student_discount_exempt: boolean;
  tax_exempt_from_category: boolean;
  student_discount_exempt_from_category: boolean;
  variants: ApiItemVariant[];
}

export interface ApiCartItem {
  id: number;
  item: number;
  variant_id: number | null;
  variant_size: string | null;
  variant_color: string | null;
  item_details: ApiItem;
  item_name: string;
  item_price: string;
  quantity: number;
  subtotal: string;
  discount_amount: string;
  customer_discount_amount: string;
  tax_amount: string;
  line_total: string;
}

export type CustomerDiscountType = '' | 'student' | 'employee';

export interface CustomerDiscountRequest {
  student_id?: string;
  use_employee_discount?: boolean;
}

export interface ApiCart {
  id: number;
  user: number;
  cart_items: ApiCartItem[];
  total_items: number;
  subtotal: string;
  discount_total: string;
  customer_discount_type: CustomerDiscountType;
  customer_discount_percent: string;
  customer_discount_amount: string;
  tax_amount: string;
  total_price: string;
}

export interface ApiSaleItem {
  item_name: string;
  item_code: string;
  variant_size: string;
  variant_color: string;
  quantity: number;
  unit_price: string;
  discount_type: 'none' | 'percent' | 'dollar';
  discount_value: string;
  discount_amount: string;
  customer_discount_amount: string;
  line_total: string;
  tax_amount: string;
}

export interface ApiSaleReceipt {
  receipt_number: string;
  issued_at: string;
  items: ApiSaleItem[];
  subtotal: string;
  discount_total: string;
  customer_discount_type: CustomerDiscountType;
  customer_discount_percent: string;
  customer_discount_amount: string;
  tax_amount: string;
  total: string;
  payment_method: 'cash' | 'card';
  cash_received: string | null;
  change_due: string;
}

export interface CheckoutPayload extends CustomerDiscountRequest {
  payment_method: 'cash' | 'card';
  cash_received?: string;
}

export interface ApiLoginResponse {
  token: string;
  user_id: number;
  role: 'Student' | 'Manager' | 'Operator';
}

export interface ApiStaffPinVerification {
  staff_authorization: string;
  expires_in: number;
}

export interface ApiStaffCartItemRemoval {
  staff_id: number;
  removed_at: string;
  item_name: string;
  quantity_removed: number;
}

export interface ApiStaffCartItemPriceChange {
  staff_id: number;
  changed_at: string;
  item_name: string;
  original_price: string;
  new_price: string;
  reason: string;
}

export interface ApiCashDrawer {
  balance: string;
  low_change_threshold: string;
  is_low: boolean;
}

export interface ApiDailySalesReport {
  date: string;
  total_money_taken_in: string;
  sales_count: number;
  category_breakdown: { category: string; total: string }[];
  receipts: ApiSaleReceipt[];
}

export interface ApiBestSellingItemsReport {
  start_date: string;
  end_date: string;
  items: { item_name: string; item_code: string; quantity_sold: number }[];
}

export interface ExemptionSettings {
  tax_exempt?: boolean;
  student_discount_exempt?: boolean;
  employee_discount_exempt?: boolean;
}

type ItemExemptionSettings = Pick<ExemptionSettings, 'tax_exempt' | 'student_discount_exempt'>;

export interface ItemPayload {
  item: string;
  item_quantity: number;
  item_price: number;
  author: string;
  item_code: string;
  isbn: string;
  badge: string;
  category: number;
  tax_exempt?: boolean;
  student_discount_exempt?: boolean;
}

export interface ItemVariantPayload {
  size: ApiItemVariant['size'];
  color: string;
  quantity: number;
}

@Injectable({ providedIn: 'root' })
export class StoreApiService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api';

  login(userId: number, password: string): Observable<ApiLoginResponse> {
    return this.http.post<ApiLoginResponse>(`${this.apiUrl}/auth/login/`, {
      user_id: userId,
      password
    });
  }

  verifyStaffPin(staffId: number, pin: string): Observable<ApiStaffPinVerification> {
    return this.http.post<ApiStaffPinVerification>(`${this.apiUrl}/auth/staff/verify-pin/`, {
      staff_id: staffId,
      pin
    });
  }

  getCashDrawer(staffAuthorization: string | null = null): Observable<ApiCashDrawer> {
    const headers = staffAuthorization
      ? new HttpHeaders({ 'X-Staff-Authorization': staffAuthorization })
      : undefined;
    return this.http.get<ApiCashDrawer>(`${this.apiUrl}/cash-drawer/`, { headers });
  }

  updateCashDrawer(balance: number, lowChangeThreshold: number): Observable<ApiCashDrawer> {
    return this.http.patch<ApiCashDrawer>(`${this.apiUrl}/cash-drawer/`, {
      balance,
      low_change_threshold: lowChangeThreshold
    });
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/auth/logout/`, {});
  }

  getCategories(): Observable<ApiCategory[]> {
    return this.http.get<ApiCategory[]>(`${this.apiUrl}/categories/`);
  }

  createCategory(categoryName: string): Observable<ApiCategory> {
    return this.http.post<ApiCategory>(`${this.apiUrl}/categories/`, {
      category_name: categoryName
    });
  }

  deleteCategory(categoryId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/categories/${categoryId}/`);
  }

  updateCategorySettings(categoryId: number, settings: ExemptionSettings): Observable<ApiCategory> {
    return this.http.patch<ApiCategory>(`${this.apiUrl}/categories/${categoryId}/`, settings);
  }

  updateCategoryDiscount(
    categoryId: number,
    discountType: 'none' | 'percent' | 'dollar',
    discountValue: number
  ): Observable<ApiCategory> {
    return this.http.patch<ApiCategory>(`${this.apiUrl}/categories/${categoryId}/`, {
      discount_type: discountType,
      discount_value: discountValue
    });
  }

  getItems(): Observable<ApiItem[]> {
    return this.http.get<ApiItem[]>(`${this.apiUrl}/items/`);
  }

  getCourseSupplyBundles(): Observable<ApiCourseSupplyBundle[]> {
    return this.http.get<ApiCourseSupplyBundle[]>(`${this.apiUrl}/bundles/`);
  }

  createCourseSupplyBundle(name: string, itemIds: number[]): Observable<ApiCourseSupplyBundle> {
    return this.http.post<ApiCourseSupplyBundle>(`${this.apiUrl}/bundles/`, {
      name,
      items: itemIds
    });
  }

  updateCourseSupplyBundle(
    bundleId: number,
    name: string,
    itemIds: number[]
  ): Observable<ApiCourseSupplyBundle> {
    return this.http.patch<ApiCourseSupplyBundle>(`${this.apiUrl}/bundles/${bundleId}/`, {
      name,
      items: itemIds
    });
  }

  deleteCourseSupplyBundle(bundleId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/bundles/${bundleId}/`);
  }

  createItem(payload: ItemPayload): Observable<ApiItem> {
    return this.http.post<ApiItem>(`${this.apiUrl}/items/`, payload);
  }

  updateItem(itemId: number, payload: ItemPayload): Observable<ApiItem> {
    return this.http.put<ApiItem>(`${this.apiUrl}/items/${itemId}/`, payload);
  }

  updateItemSettings(itemId: number, settings: ItemExemptionSettings): Observable<ApiItem> {
    return this.http.patch<ApiItem>(`${this.apiUrl}/items/${itemId}/`, settings);
  }

  deleteItem(itemId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/items/${itemId}/`);
  }

  createItemVariant(itemId: number, payload: ItemVariantPayload): Observable<ApiItemVariant> {
    return this.http.post<ApiItemVariant>(`${this.apiUrl}/items/${itemId}/variants/`, payload);
  }

  updateItemVariant(
    itemId: number,
    variantId: number,
    payload: ItemVariantPayload
  ): Observable<ApiItemVariant> {
    return this.http.patch<ApiItemVariant>(
      `${this.apiUrl}/items/${itemId}/variants/${variantId}/`,
      payload
    );
  }

  deleteItemVariant(itemId: number, variantId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/items/${itemId}/variants/${variantId}/`);
  }

  getCart(
    userId: number,
    discount: CustomerDiscountRequest,
    staffAuthorization: string | null = null
  ): Observable<ApiCart> {
    const params = new HttpParams({
      fromObject: {
        ...(discount.student_id ? { student_id: discount.student_id } : {}),
        ...(discount.use_employee_discount !== undefined
          ? { use_employee_discount: String(discount.use_employee_discount) }
          : {})
      }
    });
    const headers = staffAuthorization
      ? new HttpHeaders({ 'X-Staff-Authorization': staffAuthorization })
      : undefined;
    return this.http.get<ApiCart>(`${this.apiUrl}/users/${userId}/cart/`, { params, headers });
  }

  addCartItem(
    userId: number,
    itemId: number,
    quantity = 1,
    variantId?: number
  ): Observable<ApiCartItem> {
    return this.http.post<ApiCartItem>(`${this.apiUrl}/users/${userId}/cart/items/`, {
      item: itemId,
      quantity,
      ...(variantId !== undefined ? { variant_id: variantId } : {})
    });
  }

  updateCartItem(userId: number, cartItemId: number, quantity: number): Observable<ApiCartItem> {
    return this.http.patch<ApiCartItem>(`${this.apiUrl}/users/${userId}/cart/items/${cartItemId}/`, { quantity });
  }

  removeCartItem(userId: number, cartItemId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/users/${userId}/cart/items/${cartItemId}/`);
  }

  removeCartItemAsStaff(
    userId: number,
    cartItemId: number,
    staffAuthorization: string
  ): Observable<ApiStaffCartItemRemoval> {
    const headers = new HttpHeaders({ 'X-Staff-Authorization': staffAuthorization });
    return this.http.post<ApiStaffCartItemRemoval>(
      `${this.apiUrl}/users/${userId}/cart/items/${cartItemId}/staff-remove/`,
      {},
      { headers }
    );
  }

  changeCartItemPriceAsStaff(
    userId: number,
    cartItemId: number,
    newPrice: number,
    reason: string,
    staffAuthorization: string
  ): Observable<ApiStaffCartItemPriceChange> {
    const headers = new HttpHeaders({ 'X-Staff-Authorization': staffAuthorization });
    return this.http.post<ApiStaffCartItemPriceChange>(
      `${this.apiUrl}/users/${userId}/cart/items/${cartItemId}/staff-price-change/`,
      { new_price: newPrice, reason },
      { headers }
    );
  }

  clearCart(userId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/users/${userId}/cart/`);
  }

  checkout(
    userId: number,
    payload: CheckoutPayload,
    staffAuthorization: string | null = null
  ): Observable<ApiSaleReceipt> {
    const headers = staffAuthorization
      ? new HttpHeaders({ 'X-Staff-Authorization': staffAuthorization })
      : undefined;
    return this.http.post<ApiSaleReceipt>(`${this.apiUrl}/users/${userId}/checkout/`, payload, { headers });
  }

  getSales(): Observable<ApiSaleReceipt[]> {
    return this.http.get<ApiSaleReceipt[]>(`${this.apiUrl}/sales/`);
  }

  getDailySalesReport(date: string): Observable<ApiDailySalesReport> {
    const params = new HttpParams().set('date', date);
    return this.http.get<ApiDailySalesReport>(`${this.apiUrl}/reports/daily-sales/`, { params });
  }

  getBestSellingItemsReport(startDate: string, endDate: string): Observable<ApiBestSellingItemsReport> {
    const params = new HttpParams()
      .set('start_date', startDate)
      .set('end_date', endDate);
    return this.http.get<ApiBestSellingItemsReport>(`${this.apiUrl}/reports/best-selling-items/`, { params });
  }

  getSale(receiptNumber: string): Observable<ApiSaleReceipt> {
    return this.http.get<ApiSaleReceipt>(`${this.apiUrl}/sales/${encodeURIComponent(receiptNumber)}/`);
  }
}