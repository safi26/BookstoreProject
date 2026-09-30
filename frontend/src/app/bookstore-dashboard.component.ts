import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AuthService } from './auth.service';
import { ApiCartItem, ApiItem, ApiSaleReceipt, CheckoutPayload, ItemPayload, StoreApiService } from './store-api.service';

interface Book {
  id: number;
  title: string;
  author: string;
  category: string;
  categoryId: number;
  itemCode: string;
  price: number;
  quantity: number;
  isbn: string;
  coverUrl: string;
  coverFailed: boolean;
  badge: string;
}

interface BookDraft {
  title: string;
  author: string;
  category: string;
  itemCode: string;
  price: number;
  quantity: number;
  isbn: string;
  badge: string;
}

interface BagItem {
  book: Book;
  quantity: number;
  cartItemId: number;
}

interface ReceiptItem {
  title: string;
  itemCode: string;
  quantity: number;
  unitPrice: number;
  lineTotal: number;
}

interface SaleReceipt {
  number: string;
  issuedAt: string;
  items: ReceiptItem[];
  total: number;
  paymentMethod: 'cash' | 'card';
  cashReceived?: number;
  changeDue?: number;
}

@Component({
  selector: 'app-bookstore-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './bookstore-dashboard.component.html',
  styleUrls: []
})
export class BookstoreDashboardComponent {
  private readonly authService = inject(AuthService);
  private readonly storeApi = inject(StoreApiService);
  private readonly router = inject(Router);

  readonly signedInRole = this.authService.currentRole ?? 'Student';
  readonly isManager = this.signedInRole === 'Manager';
  readonly isStudent = this.signedInRole === 'Student';
  categories: string[] = ['All books'];
  books: Book[] = [];
  loading = true;
  apiError = '';

  searchTerm = '';
  itemCodeQuery = '';
  itemCodeMessage = '';
  itemCodeSuggestionSelected = false;
  activeItemCodeIndex = -1;
  selectedCategory = 'All books';
  newCategoryName = '';
  showBookEditor = false;
  editingBookId: number | null = null;
  bookDraft: BookDraft = this.createBookDraft();
  bag: BagItem[] = [];
  bagMessage = '';
  checkoutMessage = '';
  showBag = false;
  paymentMethod: 'cash' | 'card' = 'cash';
  cashReceived: number | null = null;
  processingPayment = false;
  receipt: SaleReceipt | null = null;
  showReceipt = false;
  editorError = '';

  constructor() {
    this.loadCatalog();
  }

  get filteredBooks(): Book[] {
    const query = this.searchTerm.trim().toLowerCase();

    return this.books.filter(book => {
      const matchesCategory = this.selectedCategory === 'All books' || book.category === this.selectedCategory;
      const matchesSearch = !query || `${book.title} ${book.author} ${book.category}`.toLowerCase().includes(query);
      return matchesCategory && matchesSearch;
    });
  }

  get matchingItemCodes(): Book[] {
    const query = this.itemCodeQuery.trim().toUpperCase();
    if (!this.isStudent || !query || this.itemCodeSuggestionSelected) {
      return [];
    }

    return this.books
      .filter(book => book.itemCode.toUpperCase().startsWith(query))
      .slice(0, 6);
  }

  get activeItemCodeSuggestionId(): string | null {
    const book = this.matchingItemCodes[this.activeItemCodeIndex];
    return book ? `item-code-option-${book.id}` : null;
  }

  get bagCount(): number {
    return this.bag.reduce((count, item) => count + item.quantity, 0);
  }

  get bagTotal(): number {
    return this.bag.reduce((total, item) => total + item.book.price * item.quantity, 0);
  }

  get changeDue(): number {
    return Math.max(0, Number(this.cashReceived ?? 0) - this.bagTotal);
  }

  onCoverLoaded(book: Book, event: Event): void {
    const image = event.target;
    if (image instanceof HTMLImageElement && image.naturalWidth <= 1) {
      book.coverFailed = true;
    }
  }

  get canCompleteStudentSale(): boolean {
    return this.isStudent && this.bag.length > 0 &&
      (this.paymentMethod === 'card' || (this.cashReceived !== null && Number(this.cashReceived) >= this.bagTotal));
  }

  addByItemCode(): void {
    if (!this.isStudent) {
      return;
    }

    const code = this.itemCodeQuery.trim().toUpperCase();
    const book = this.books.find(item => item.itemCode.toUpperCase() === code);

    if (!book) {
      this.itemCodeMessage = code ? `No item found for code ${code}.` : 'Enter an item code.';
      return;
    }

    this.addToBag(book);
    this.itemCodeMessage = `Adding ${book.title} to your cart...`;
    this.itemCodeQuery = '';
  }

  selectItemCode(book: Book): void {
    if (!this.isStudent) {
      return;
    }

    this.itemCodeQuery = book.itemCode;
    this.itemCodeMessage = '';
    this.itemCodeSuggestionSelected = true;
    this.activeItemCodeIndex = -1;
  }

  onItemCodeQueryChange(): void {
    this.itemCodeSuggestionSelected = false;
    this.activeItemCodeIndex = -1;
  }

  handleItemCodeKeydown(event: KeyboardEvent): void {
    const suggestions = this.matchingItemCodes;

    if (event.key === 'ArrowDown' && suggestions.length) {
      event.preventDefault();
      this.activeItemCodeIndex = (this.activeItemCodeIndex + 1) % suggestions.length;
    } else if (event.key === 'ArrowUp' && suggestions.length) {
      event.preventDefault();
      this.activeItemCodeIndex = this.activeItemCodeIndex <= 0 ? suggestions.length - 1 : this.activeItemCodeIndex - 1;
    } else if (event.key === 'Enter' && this.activeItemCodeIndex >= 0 && suggestions[this.activeItemCodeIndex]) {
      event.preventDefault();
      this.selectItemCode(suggestions[this.activeItemCodeIndex]);
    } else if (event.key === 'Escape') {
      this.activeItemCodeIndex = -1;
    }
  }

  addToBag(book: Book): void {
    if (this.isManager) {
      return;
    }

    const userId = this.authService.currentUserId;
    if (userId === null) {
      this.bagMessage = 'Use a numeric Django user ID to save items to your cart.';
      if (this.isStudent) {
        this.itemCodeMessage = this.bagMessage;
      }
      return;
    }

    this.storeApi.addCartItem(userId, book.id).subscribe({
      next: () => {
        this.loadCart();
        this.bagMessage = `${book.title} added to your bag.`;
        if (this.isStudent) {
          this.itemCodeMessage = `${book.title} added to your cart.`;
        }
        this.checkoutMessage = '';
      },
      error: error => {
        const message = this.getApiError(error, 'Could not add this item to your cart.');
        this.bagMessage = message;
        if (this.isStudent) {
          this.itemCodeMessage = message;
        }
      }
    });
  }

  changeQuantity(item: BagItem, change: number): void {
    const userId = this.authService.currentUserId;
    const quantity = item.quantity + change;
    if (userId === null) {
      this.checkoutMessage = 'Use a numeric Django user ID to update your cart.';
      return;
    }

    if (quantity < 1) {
      this.removeFromBag(item);
      return;
    }

    this.storeApi.updateCartItem(userId, item.cartItemId, quantity).subscribe({
      next: () => {
        this.loadCart();
        this.checkoutMessage = '';
      },
      error: error => this.checkoutMessage = this.getApiError(error, 'Could not update your cart.')
    });
  }

  removeFromBag(item: BagItem): void {
    const userId = this.authService.currentUserId;
    if (userId === null) {
      this.checkoutMessage = 'Use a numeric Django user ID to update your cart.';
      return;
    }

    this.storeApi.removeCartItem(userId, item.cartItemId).subscribe({
      next: () => {
        this.loadCart();
        this.checkoutMessage = '';
      },
      error: error => this.checkoutMessage = this.getApiError(error, 'Could not remove this item.')
    });
  }

  checkout(): void {
    this.checkoutMessage = 'Checkout is not connected yet. Your bag is saved while you browse.';
  }

  completeStudentSale(): void {
    if (!this.canCompleteStudentSale || this.processingPayment) {
      return;
    }

    const userId = this.authService.currentUserId;
    if (userId === null) {
      this.checkoutMessage = 'Use a numeric Django user ID to complete this demo checkout.';
      return;
    }

    const payload: CheckoutPayload = {
      payment_method: this.paymentMethod,
      ...(this.paymentMethod === 'cash'
        ? { cash_received: Number(this.cashReceived).toFixed(2) }
        : {})
    };
    this.processingPayment = true;
    this.checkoutMessage = '';
    this.storeApi.checkout(userId, payload).subscribe({
      next: receipt => this.finishStudentSale(receipt),
      error: error => {
        this.processingPayment = false;
        this.checkoutMessage = this.getApiError(error, 'Could not complete the payment. Your cart has not been changed.');
      }
    });
  }

  private finishStudentSale(receipt: ApiSaleReceipt): void {
    this.receipt = {
      number: receipt.receipt_number,
      issuedAt: new Date(receipt.issued_at).toLocaleString(),
      items: receipt.items.map(item => ({
        title: item.item_name,
        itemCode: item.item_code,
        quantity: item.quantity,
        unitPrice: Number(item.unit_price),
        lineTotal: Number(item.line_total)
      })),
      total: Number(receipt.total),
      paymentMethod: receipt.payment_method,
      ...(receipt.cash_received !== null
        ? { cashReceived: Number(receipt.cash_received), changeDue: Number(receipt.change_due) }
        : {})
    };

    this.bag = [];
    this.cashReceived = null;
    this.paymentMethod = 'cash';
    this.processingPayment = false;
    this.showBag = false;
    this.showReceipt = true;
    this.loadCatalog();
  }

  closeReceipt(): void {
    this.showReceipt = false;
    this.receipt = null;
  }

  openBookEditor(book?: Book): void {
    if (!this.isManager) {
      return;
    }

    this.editingBookId = book?.id ?? null;
    this.bookDraft = book ? {
      title: book.title,
      author: book.author,
      category: book.category,
      itemCode: book.itemCode,
      price: book.price,
      quantity: book.quantity,
      isbn: book.isbn,
      badge: book.badge
    } : this.createBookDraft();
    this.editorError = '';
    this.showBookEditor = true;
  }

  saveBook(): void {
    if (!this.isManager || !this.bookDraft.title.trim() || this.bookDraft.category === 'All books') {
      return;
    }

    const category = this.categories.find(item => item === this.bookDraft.category);
    if (!category) {
      this.editorError = 'Choose a category from the list.';
      return;
    }

    const categoryId = this.categoryIds.get(category);
    if (categoryId === undefined) {
      this.editorError = 'The selected category is not available. Reload and try again.';
      return;
    }

    const payload: ItemPayload = {
      item: this.bookDraft.title.trim(),
      item_quantity: Number(this.bookDraft.quantity),
      item_price: Number(this.bookDraft.price),
      author: this.bookDraft.author.trim(),
      item_code: this.bookDraft.itemCode.trim(),
      isbn: this.bookDraft.isbn.trim(),
      badge: this.bookDraft.badge.trim(),
      category: categoryId
    };

    const request = this.editingBookId === null
      ? this.storeApi.createItem(payload)
      : this.storeApi.updateItem(this.editingBookId, payload);
    request.subscribe({
      next: () => {
        this.closeBookEditor();
        this.loadCatalog();
      },
      error: error => this.editorError = this.getApiError(error, 'Could not save this item.')
    });
  }

  removeBook(book: Book): void {
    if (!this.isManager) {
      return;
    }

    this.storeApi.deleteItem(book.id).subscribe({
      next: () => this.loadCatalog(),
      error: error => this.apiError = this.getApiError(error, 'Could not remove this item.')
    });
  }

  addCategory(): void {
    if (!this.isManager) {
      return;
    }

    const name = this.newCategoryName.trim();
    if (!name || this.categories.some(category => category.toLowerCase() === name.toLowerCase())) {
      return;
    }

    this.storeApi.createCategory(name).subscribe({
      next: category => {
        this.categoryIds.set(category.category_name, category.category_id);
        this.categories = [...this.categories, category.category_name];
        this.newCategoryName = '';
        this.selectedCategory = category.category_name;
      },
      error: error => this.apiError = this.getApiError(error, 'Could not create this category.')
    });
  }

  closeBookEditor(): void {
    this.showBookEditor = false;
    this.editingBookId = null;
    this.bookDraft = this.createBookDraft();
    this.editorError = '';
  }

  signOut(): void {
    this.authService.signOut();
    void this.router.navigateByUrl('/');
  }

  private createBookDraft(): BookDraft {
    const nextItemCode = Math.max(0, ...this.books.map(book => {
      const match = /^BK-(\d+)$/.exec(book.itemCode);
      return match ? Number(match[1]) : 0;
    })) + 1;

    return {
      title: '',
      author: '',
      category: this.categories[1] ?? '',
      itemCode: `BK-${String(nextItemCode).padStart(4, '0')}`,
      price: 18,
      quantity: 1,
      isbn: '',
      badge: ''
    };
  }

  private readonly categoryIds = new Map<string, number>();

  private loadCatalog(): void {
    this.loading = true;
    this.apiError = '';
    forkJoin({
      categories: this.storeApi.getCategories(),
      items: this.storeApi.getItems()
    }).subscribe({
      next: ({ categories, items }) => {
        this.categoryIds.clear();
        for (const category of categories) {
          this.categoryIds.set(category.category_name, category.category_id);
        }
        this.categories = ['All books', ...categories.map(category => category.category_name)];
        this.books = items.map(item => this.toBook(item));
        this.loading = false;
        if (this.authService.currentUserId !== null) {
          this.loadCart();
        }
      },
      error: error => {
        this.loading = false;
        this.apiError = this.getApiError(error, 'Could not load the catalog. Check that the backend is running.');
      }
    });
  }

  private toBook(item: ApiItem): Book {
    return {
      id: item.item_id,
      title: item.item,
      author: item.author,
      category: item.category_name,
      categoryId: item.category,
      itemCode: item.item_code || `ITEM-${item.item_id}`,
      price: Number(item.item_price),
      quantity: item.item_quantity,
      isbn: item.isbn,
      coverUrl: item.cover_url,
      coverFailed: false,
      badge: item.badge
    };
  }

  private loadCart(): void {
    const userId = this.authService.currentUserId;
    if (userId === null) {
      this.bag = [];
      return;
    }

    this.storeApi.getCart(userId).subscribe({
      next: cart => {
        this.bag = cart.cart_items.map((cartItem: ApiCartItem) => ({
          book: this.toBook(cartItem.item_details),
          quantity: cartItem.quantity,
          cartItemId: cartItem.id
        }));
      },
      error: error => this.bagMessage = this.getApiError(error, 'Could not load your cart.')
    });
  }

  private getApiError(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.error ?? error.error?.detail;
      if (typeof detail === 'string') {
        return detail;
      }
    }

    return fallback;
  }
}
