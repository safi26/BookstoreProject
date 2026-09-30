import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface ApiCategory {
  category_id: number;
  category_name: string;
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
}

export interface ApiCartItem {
  id: number;
  item: number;
  item_details: ApiItem;
  item_name: string;
  item_price: string;
  quantity: number;
  subtotal: number;
}

export interface ApiCart {
  id: number;
  user: number;
  cart_items: ApiCartItem[];
  total_items: number;
  total_price: number;
}

export interface ApiSaleItem {
  item_name: string;
  item_code: string;
  quantity: number;
  unit_price: string;
  line_total: string;
}

export interface ApiSaleReceipt {
  receipt_number: string;
  issued_at: string;
  items: ApiSaleItem[];
  total: string;
  payment_method: 'cash' | 'card';
  cash_received: string | null;
  change_due: string;
}

export interface CheckoutPayload {
  payment_method: 'cash' | 'card';
  cash_received?: string;
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
}

@Injectable({ providedIn: 'root' })
export class StoreApiService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api';

  getCategories(): Observable<ApiCategory[]> {
    return this.http.get<ApiCategory[]>(`${this.apiUrl}/categories/`);
  }

  createCategory(category_name: string): Observable<ApiCategory> {
    return this.http.post<ApiCategory>(`${this.apiUrl}/categories/`, { category_name });
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

  deleteItem(itemId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/items/${itemId}/`);
  }

  getCart(userId: number): Observable<ApiCart> {
    return this.http.get<ApiCart>(`${this.apiUrl}/users/${userId}/cart/`);
  }

  addCartItem(userId: number, itemId: number, quantity = 1): Observable<ApiCartItem> {
    return this.http.post<ApiCartItem>(`${this.apiUrl}/users/${userId}/cart/items/`, {
      item: itemId,
      quantity
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
}