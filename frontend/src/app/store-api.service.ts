import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface ApiCategory {
  category_id: number;
  category_name: string;
  tax_exempt: boolean;
  discount_type: 'none' | 'percent' | 'dollar';
  discount_value: string;
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
  tax_amount: string;
  line_total: string;
}

export interface ApiCart {
  id: number;
  user: number;
  cart_items: ApiCartItem[];
  total_items: number;
  subtotal: string;
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
  line_total: string;
  tax_amount: string;
}

export interface ApiSaleReceipt {
  receipt_number: string;
  issued_at: string;
  items: ApiSaleItem[];
  subtotal: string;
  discount_total: string;
  tax_amount: string;
  total: string;
  payment_method: 'cash' | 'card';
  cash_received: string | null;
  change_due: string;
}

export interface CheckoutPayload {
  payment_method: 'cash' | 'card';
  cash_received?: string;
}

export interface ApiLoginResponse {
  token: string;
  user_id: number;
  role: 'Student' | 'Manager';
}

export interface ItemPayload {
  item: string;
  item_quantity: number;
  item_price: number;
  author: string;
  item_code: string;
  isbn: string;
  badge: string;
  category: number;
  tax_exempt: boolean;
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

  updateCategoryTaxExemption(categoryId: number, taxExempt: boolean): Observable<ApiCategory> {
    return this.http.patch<ApiCategory>(`${this.apiUrl}/categories/${categoryId}/`, {
      tax_exempt: taxExempt
    });
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

  createItem(payload: ItemPayload): Observable<ApiItem> {
    return this.http.post<ApiItem>(`${this.apiUrl}/items/`, payload);
  }

  updateItem(itemId: number, payload: ItemPayload): Observable<ApiItem> {
    return this.http.put<ApiItem>(`${this.apiUrl}/items/${itemId}/`, payload);
  }

  updateItemTaxExemption(itemId: number, taxExempt: boolean): Observable<ApiItem> {
    return this.http.patch<ApiItem>(`${this.apiUrl}/items/${itemId}/`, {
      tax_exempt: taxExempt
    });
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

  getCart(userId: number): Observable<ApiCart> {
    return this.http.get<ApiCart>(`${this.apiUrl}/users/${userId}/cart/`);
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

  clearCart(userId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/users/${userId}/cart/`);
  }

  checkout(userId: number, payload: CheckoutPayload): Observable<ApiSaleReceipt> {
    return this.http.post<ApiSaleReceipt>(`${this.apiUrl}/users/${userId}/checkout/`, payload);
  }

  getSales(): Observable<ApiSaleReceipt[]> {
    return this.http.get<ApiSaleReceipt[]>(`${this.apiUrl}/sales/`);
  }

  getSale(receiptNumber: string): Observable<ApiSaleReceipt> {
    return this.http.get<ApiSaleReceipt>(`${this.apiUrl}/sales/${encodeURIComponent(receiptNumber)}/`);
  }
}