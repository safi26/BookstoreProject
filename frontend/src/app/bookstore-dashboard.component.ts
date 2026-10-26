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
  isProductImage: boolean;
  badge: string;
  taxExempt: boolean;
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
  taxExempt: boolean;
}

interface BagItem {
  book: Book;
  quantity: number;
  cartItemId: number;
  subtotal: number;
  taxAmount: number;
}

interface ReceiptItem {
  title: string;
  itemCode: string;
  quantity: number;
  unitPrice: number;
  lineTotal: number;
  taxAmount: number;
  totalWithTax: number;
}

interface SaleReceipt {
  number: string;
  issuedAt: string;
  items: ReceiptItem[];
  subtotal: number;
  taxAmount: number;
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
  categories: string[] = ['All items'];
  books: Book[] = [];
  loading = true;
  apiError = '';

  searchTerm = '';
  itemCodeQuery = '';
  itemCodeMessage = '';
  itemCodeSuggestionSelected = false;
  activeItemCodeIndex = -1;
  selectedCategory = 'All items';
  showCategoryCreator = false;
  categoryDraft = '';
  categoryError = '';
  creatingCategory = false;
  deletingCategory = false;
  showBookEditor = false;
  editingBookId: number | null = null;
  bookDraft: BookDraft = this.createBookDraft();
  bag: BagItem[] = [];
  bagMessage = '';
  checkoutMessage = '';
  showBag = false;
  showSalesHistory = false;
  salesHistoryLoading = false;
  salesHistoryError = '';
  salesSearch = '';
  salesHistory: SaleReceipt[] = [];
  paymentMethod: 'cash' | 'card' = 'cash';
  cashReceived: number | null = null;
  showCardDialog = false;
  cardholderName = '';
  cardNumber = '';
  cardExpiryMonth = '';
  cardExpiryYear = '';
  cardCvv = '';
  cardCvvFocused = false;
  readonly cardExpiryYears = Array.from(
    { length: 16 },
    (_, index) => new Date().getFullYear() + index
  );
  private readonly itemIllustrationGraphics: Record<string, string> = {
    'Campus Hoodie': `
      <path d="M235 150c12-29 34-45 65-45s53 16 65 45l52 28 49 58-43 44-34-31v181H211V249l-34 31-43-44 49-58z"
        fill="#315e4a" stroke="#19352f" stroke-width="9" stroke-linejoin="round"/>
      <path d="M270 116c4 41 54 41 60 0" fill="none" stroke="#d6e3da" stroke-width="11"/>
      <path d="M300 160v66m-20-53 20 29 20-29" fill="none" stroke="#d6e3da" stroke-width="7" stroke-linecap="round"/>
      <path d="M246 333v56q54 35 108 0v-56" fill="#234638" stroke="#19352f" stroke-width="7" stroke-linejoin="round"/>
      <path d="M148 240l-25 25 30 30 31-29m268-26 25 25-30 30-31-29M220 404h160"
        fill="none" stroke="#19352f" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
    `,
    'Scientific Calculator Sleeve': `
      <rect x="202" y="102" width="196" height="416" rx="24" fill="#435a4f" stroke="#19352f" stroke-width="10"/>
      <rect x="226" y="132" width="148" height="92" rx="8" fill="#d8e5cf" stroke="#19352f" stroke-width="7"/>
      <text x="358" y="194" text-anchor="end" fill="#19352f" font-family="monospace" font-size="38">2.718</text>
      <g fill="#f0f4ef" stroke="#19352f" stroke-width="5">
        <rect x="225" y="248" width="38" height="38" rx="8"/><rect x="277" y="248" width="38" height="38" rx="8"/><rect x="329" y="248" width="38" height="38" rx="8"/>
        <rect x="225" y="300" width="38" height="38" rx="8"/><rect x="277" y="300" width="38" height="38" rx="8"/><rect x="329" y="300" width="38" height="38" rx="8"/>
        <rect x="225" y="352" width="38" height="38" rx="8"/><rect x="277" y="352" width="38" height="38" rx="8"/><rect x="329" y="352" width="38" height="38" rx="8"/>
        <rect x="225" y="404" width="38" height="38" rx="8"/><rect x="277" y="404" width="38" height="38" rx="8"/><rect x="329" y="404" width="38" height="38" rx="8"/>
      </g>
      <g fill="#315e4a">
        <circle cx="244" cy="267" r="6"/><circle cx="296" cy="267" r="6"/><circle cx="348" cy="267" r="6"/>
        <circle cx="244" cy="319" r="6"/><circle cx="296" cy="319" r="6"/><circle cx="348" cy="319" r="6"/>
        <circle cx="244" cy="371" r="6"/><circle cx="296" cy="371" r="6"/><circle cx="348" cy="371" r="6"/>
        <circle cx="244" cy="423" r="6"/><circle cx="296" cy="423" r="6"/><circle cx="348" cy="423" r="6"/>
      </g>
    `
  };
  private readonly itemIllustrations: Record<string, string> = {
    'Trail Mix': '🥜',
    'Cinnamon Oat Bites': '🍪',
    'Fruit Leather Sticks': '🍓',
    'Cold Brew': '🧋',
    'Sparkling Lemonade': '🍋',
    'Iced Tea': '🍹',
    'Premium Notebook': '📓',
    'Mechanical Pencil Set': '✏️',
    'Sticky Note Pack': '🗒️',
    'Blue Book Exam Pad': '📝',
    'Scientific Calculator Sleeve': '🧮',
    'Highlighter Trio': '🖍️',
    'Watercolor Set': '🎨',
    'Sketchbook Pack': '📒',
    'Brush Kit': '🖌️',
    'Campus Hoodie': '🧥',
    'Cotton Crew Socks': '🧦',
    'Canvas Tote Bag': '👜',
    'Lab Manual Binder': '📕',
    'USB Drive 32GB': '💾',
    'Three-Ring Binder Set': '🗂️'
  };
  private readonly categoryIllustrations: Record<string, string> = {
    'Snacks': '🥨',
    'Drinks': '🥤',
    'Stationery': '📚',
    'Exam Supplies': '📝',
    'Art Supplies': '🎨',
    'Apparel': '🧥',
    'Course Supplies': '📚',
    'Books': '📖'
  };
  processingPayment = false;
  receipt: SaleReceipt | null = null;
  showReceipt = false;
  editorError = '';
  taxExemptionError = '';
  taxExemptionUpdating = false;
  cancellingTransaction = false;

  constructor() {
    this.loadCatalog();
  }

  get filteredBooks(): Book[] {
    const query = this.searchTerm.trim().toLowerCase();

    return this.books.filter(book => {
      const matchesCategory = this.selectedCategory === 'All items' || book.category === this.selectedCategory;
      const matchesSearch = !query ||
        `${book.title} ${book.author} ${book.category} ${book.itemCode}`.toLowerCase().includes(query);
      return matchesCategory && matchesSearch;
    });
  }

  get filteredSales(): SaleReceipt[] {
    const query = this.salesSearch.trim().toLowerCase();
    if (!query) {
      return this.salesHistory;
    }

    return this.salesHistory.filter(sale =>
      `${sale.number} ${sale.issuedAt} ${sale.items.map(item => `${item.title} ${item.itemCode}`).join(' ')}`
        .toLowerCase()
        .includes(query)
    );
  }

  get categoryPreviewBooks(): Book[] {
    const categoryItems = this.books.filter(book =>
      this.selectedCategory === 'All items' || book.category === this.selectedCategory
    );
    return categoryItems.slice(0, 4);
  }

  get selectedCategoryTaxExempt(): boolean {
    const categoryId = this.categoryIds.get(this.selectedCategory);
    return categoryId === undefined ? false : this.categoryTaxExemptById.get(categoryId) ?? false;
  }

  isBookTaxExempt(book: Book): boolean {
    return book.taxExempt || (this.categoryTaxExemptById.get(book.categoryId) ?? false);
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

  get bagSubtotal(): number {
    return this.bag.reduce((total, item) => total + item.subtotal, 0);
  }

  get bagTax(): number {
    return this.bag.reduce((total, item) => total + item.taxAmount, 0);
  }

  get bagTotal(): number {
    return this.bagSubtotal + this.bagTax;
  }

  get changeDue(): number {
    return Math.max(0, Number(this.cashReceived ?? 0) - this.bagTotal);
  }

  get cardExpiryIsValid(): boolean {
    if (!this.cardExpiryMonth || !this.cardExpiryYear) {
      return false;
    }

    return !this.cardExpiryIsPast;
  }

  get cardExpiryIsPast(): boolean {
    if (!this.cardExpiryMonth || !this.cardExpiryYear) {
      return false;
    }

    const year = Number(this.cardExpiryYear);
    const month = Number(this.cardExpiryMonth);
    const now = new Date();
    return year < now.getFullYear() ||
      (year === now.getFullYear() && month < now.getMonth() + 1);
  }

  get cardExpiryIsPartial(): boolean {
    return Boolean(this.cardExpiryMonth) !== Boolean(this.cardExpiryYear);
  }

  get cardholderNameIsValid(): boolean {
    const name = this.cardholderName.trim();
    return name.length > 0 && !/\d/.test(name);
  }

  get cardNumberIsValid(): boolean {
    return /^\d{16}$/.test(this.cardNumber);
  }

  get cardNumberHasOnlyDigits(): boolean {
    return /^\d+$/.test(this.cardNumber);
  }

  get cardCvvIsValid(): boolean {
    return /^\d{3}$/.test(this.cardCvv);
  }

  get cardCvvHasOnlyDigits(): boolean {
    return /^\d+$/.test(this.cardCvv);
  }

  onCoverLoaded(book: Book, event: Event): void {
    const image = event.target;
    if (image instanceof HTMLImageElement && image.naturalWidth <= 1) {
      book.coverFailed = true;
    }
  }

  get canCompleteStudentSale(): boolean {
    return this.isStudent && this.bag.length > 0 &&
      (this.paymentMethod === 'card'
        ? this.cardholderNameIsValid &&
          this.cardNumberIsValid &&
          this.cardExpiryIsValid &&
          this.cardCvvIsValid
        : this.cashReceived !== null && Number(this.cashReceived) >= this.bagTotal);
  }

  selectPaymentMethod(method: 'cash' | 'card'): void {
    this.paymentMethod = method;
    this.checkoutMessage = '';
    if (method === 'card') {
      this.cardCvvFocused = false;
      this.showCardDialog = true;
      return;
    }

    this.showCardDialog = false;
    this.clearCardDetails();
  }

  closeCardDialog(): void {
    if (this.processingPayment) {
      return;
    }

    this.showCardDialog = false;
    this.clearCardDetails();
    this.checkoutMessage = '';
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

  cancelStudentTransaction(): void {
    if (!this.isStudent || this.processingPayment || this.cancellingTransaction) {
      return;
    }

    const userId = this.authService.currentUserId;
    if (userId === null) {
      this.checkoutMessage = 'Use a numeric Django user ID to cancel your transaction.';
      return;
    }

    this.cancellingTransaction = true;
    this.checkoutMessage = '';
    this.storeApi.clearCart(userId).subscribe({
      next: () => {
        this.bag = [];
        this.cashReceived = null;
        this.paymentMethod = 'cash';
        this.clearCardDetails();
        this.showCardDialog = false;
        this.showBag = false;
        this.itemCodeQuery = '';
        this.itemCodeMessage = '';
        this.bagMessage = 'Transaction canceled. Cart cleared; inventory was not changed.';
        this.loadCart();
        this.cancellingTransaction = false;
      },
      error: error => {
        this.checkoutMessage = this.getApiError(error, 'Could not cancel the transaction. Your cart has not been changed.');
        this.cancellingTransaction = false;
      }
    });
  }

  completeStudentSale(): void {
    if (!this.canCompleteStudentSale || this.processingPayment || this.cancellingTransaction) {
      return;
    }

    const userId = this.authService.currentUserId;
    if (userId === null) {
      this.checkoutMessage = 'Use a numeric Django user ID to complete this demo checkout.';
      return;
    }

    if (this.paymentMethod === 'card' && this.cardNumber.replace(/[\s-]/g, '').endsWith('0000')) {
      this.clearCardDetails();
      this.checkoutMessage = 'Card declined in demo. Your cart has not been changed and no charge was made.';
      return;
    }

    const payload: CheckoutPayload = {
      payment_method: this.paymentMethod,
      ...(this.paymentMethod === 'cash'
        ? { cash_received: Number(this.cashReceived).toFixed(2) }
        : {})
    };
    this.clearCardDetails();
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
    this.receipt = this.toSaleReceipt(receipt);

    this.bag = [];
    this.cashReceived = null;
    this.clearCardDetails();
    this.showCardDialog = false;
    this.paymentMethod = 'cash';
    this.processingPayment = false;
    this.showBag = false;
    this.showReceipt = true;
    this.loadCatalog();
  }

  private toSaleReceipt(receipt: ApiSaleReceipt): SaleReceipt {
    return {
      number: receipt.receipt_number,
      issuedAt: new Date(receipt.issued_at).toLocaleString(),
      items: receipt.items.map(item => ({
        title: item.item_name,
        itemCode: item.item_code,
        quantity: item.quantity,
        unitPrice: Number(item.unit_price),
        lineTotal: Number(item.line_total),
        taxAmount: Number(item.tax_amount),
        totalWithTax: Number(item.line_total) + Number(item.tax_amount)
      })),
      subtotal: Number(receipt.subtotal),
      taxAmount: Number(receipt.tax_amount),
      total: Number(receipt.total),
      paymentMethod: receipt.payment_method,
      ...(receipt.cash_received !== null
        ? { cashReceived: Number(receipt.cash_received), changeDue: Number(receipt.change_due) }
        : {})
    };
  }

  openSalesHistory(): void {
    if (!this.isManager || this.salesHistoryLoading) {
      return;
    }

    this.showSalesHistory = true;
    this.salesHistoryLoading = true;
    this.salesHistoryError = '';
    this.storeApi.getSales().subscribe({
      next: sales => {
        this.salesHistory = sales.map(sale => this.toSaleReceipt(sale));
        this.salesHistoryLoading = false;
      },
      error: error => {
        this.salesHistoryError = this.getApiError(error, 'Could not load sales history.');
        this.salesHistoryLoading = false;
      }
    });
  }

  closeSalesHistory(): void {
    this.showSalesHistory = false;
    this.salesSearch = '';
  }

  closeReceipt(): void {
    this.showReceipt = false;
    this.receipt = null;
  }

  private clearCardDetails(): void {
    this.cardholderName = '';
    this.cardNumber = '';
    this.cardExpiryMonth = '';
    this.cardExpiryYear = '';
    this.cardCvv = '';
    this.cardCvvFocused = false;
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
      badge: book.badge,
      taxExempt: book.taxExempt
    } : this.createBookDraft();
    this.editorError = '';
    this.showBookEditor = true;
  }

  saveBook(): void {
    if (!this.isManager || !this.bookDraft.title.trim() || this.bookDraft.category === 'All items') {
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
      category: categoryId,
      tax_exempt: this.bookDraft.taxExempt
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

  createCategory(): void {
    if (!this.isManager || this.creatingCategory) {
      return;
    }

    const categoryName = this.categoryDraft.trim();
    if (!categoryName) {
      this.categoryError = 'Enter a category name.';
      return;
    }

    if (this.categories.some(category => category.toLowerCase() === categoryName.toLowerCase())) {
      this.categoryError = 'A category with this name already exists.';
      return;
    }

    this.creatingCategory = true;
    this.categoryError = '';
    this.storeApi.createCategory(categoryName).subscribe({
      next: category => {
        this.categoryIds.set(category.category_name, category.category_id);
        this.categoryTaxExemptById.set(category.category_id, category.tax_exempt);
        this.categories = [
          'All items',
          ...this.categories.slice(1).concat(category.category_name).sort((a, b) => a.localeCompare(b))
        ];
        this.selectedCategory = category.category_name;
        this.categoryDraft = '';
        this.showCategoryCreator = false;
        this.creatingCategory = false;
      },
      error: error => {
        this.categoryError = this.getApiError(error, 'Could not create this category.');
        this.creatingCategory = false;
      }
    });
  }

  categoryItemCount(categoryName: string): number {
    return this.books.filter(book => book.category === categoryName).length;
  }

  deleteCategory(categoryName: string): void {
    if (!this.isManager || this.deletingCategory) {
      return;
    }

    const categoryId = this.categoryIds.get(categoryName);
    if (categoryId === undefined) {
      this.categoryError = 'The selected category is not available. Reload and try again.';
      return;
    }

    if (this.categoryItemCount(categoryName) > 0) {
      this.categoryError = `Move or remove "${categoryName}" items before deleting this category.`;
      return;
    }

    if (!window.confirm(`Delete the "${categoryName}" category? This cannot be undone.`)) {
      return;
    }

    this.deletingCategory = true;
    this.categoryError = '';
    this.storeApi.deleteCategory(categoryId).subscribe({
      next: () => {
        this.categoryIds.delete(categoryName);
        this.categoryTaxExemptById.delete(categoryId);
        this.categories = this.categories.filter(category => category !== categoryName);
        if (this.selectedCategory === categoryName) {
          this.selectedCategory = 'All items';
        }
        this.deletingCategory = false;
      },
      error: error => {
        this.categoryError = this.getApiError(error, 'Could not delete this category.');
        this.deletingCategory = false;
      }
    });
  }

  setCategoryTaxExempt(event: Event): void {
    if (!this.isManager || this.taxExemptionUpdating) {
      return;
    }

    const categoryId = this.categoryIds.get(this.selectedCategory);
    const target = event.target;
    if (categoryId === undefined || !(target instanceof HTMLInputElement)) {
      return;
    }

    this.taxExemptionUpdating = true;
    this.taxExemptionError = '';
    this.storeApi.updateCategoryTaxExemption(categoryId, target.checked).subscribe({
      next: category => {
        this.categoryTaxExemptById.set(category.category_id, category.tax_exempt);
        this.taxExemptionUpdating = false;
      },
      error: error => {
        this.taxExemptionError = this.getApiError(error, 'Could not update this category exemption.');
        this.taxExemptionUpdating = false;
      }
    });
  }

  setItemTaxExempt(book: Book, event: Event): void {
    if (!this.isManager || this.taxExemptionUpdating) {
      return;
    }

    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }

    this.taxExemptionUpdating = true;
    this.taxExemptionError = '';
    this.storeApi.updateItemTaxExemption(book.id, target.checked).subscribe({
      next: item => {
        book.taxExempt = item.tax_exempt;
        this.taxExemptionUpdating = false;
      },
      error: error => {
        this.taxExemptionError = this.getApiError(error, 'Could not update this item exemption.');
        this.taxExemptionUpdating = false;
      }
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
      const match = /^(?:BK|ITM)-(\d+)$/.exec(book.itemCode);
      return match ? Number(match[1]) : 0;
    })) + 1;

    return {
      title: '',
      author: '',
      category: this.categories[1] ?? '',
      itemCode: `ITM-${String(nextItemCode).padStart(4, '0')}`,
      price: 18,
      quantity: 1,
      isbn: '',
      badge: '',
      taxExempt: false
    };
  }

  private readonly categoryIds = new Map<string, number>();
  private readonly categoryTaxExemptById = new Map<number, boolean>();

  private loadCatalog(): void {
    this.loading = true;
    this.apiError = '';
    forkJoin({
      categories: this.storeApi.getCategories(),
      items: this.storeApi.getItems()
    }).subscribe({
      next: ({ categories, items }) => {
        this.categoryIds.clear();
        this.categoryTaxExemptById.clear();
        for (const category of categories) {
          this.categoryIds.set(category.category_name, category.category_id);
          this.categoryTaxExemptById.set(category.category_id, category.tax_exempt);
        }
        this.categories = ['All items', ...categories.map(category => category.category_name)];
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
    const hasBookCover = Boolean(item.isbn);
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
      coverUrl: item.cover_url || (hasBookCover ? '' : this.createProductIllustration(item)),
      coverFailed: false,
      isProductImage: !hasBookCover,
      badge: item.badge,
      taxExempt: item.tax_exempt
    };
  }

  private createProductIllustration(item: ApiItem): string {
    const illustration = this.itemIllustrations[item.item] ??
      this.categoryIllustrations[item.category_name] ??
      '📦';
    const graphic = this.itemIllustrationGraphics[item.item] ??
      `<text x="300" y="380" text-anchor="middle" font-size="190" font-family="Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif">${illustration}</text>`;
    const title = this.escapeXml(item.item);
    const category = this.escapeXml(item.category_name.toUpperCase());
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 760">
      <rect width="600" height="760" fill="#e7eee7"/>
      <circle cx="300" cy="310" r="205" fill="#d6e3da"/>
      <circle cx="300" cy="310" r="164" fill="#f8faf6"/>
      ${graphic}
      <path d="M70 548h460" stroke="#c5d4c8" stroke-width="2"/>
      <text x="300" y="594" text-anchor="middle" fill="#52695d" font-family="Arial, sans-serif" font-size="18" font-weight="700" letter-spacing="4">${category}</text>
      <text x="300" y="650" text-anchor="middle" fill="#19352f" font-family="Georgia, serif" font-size="30">${title}</text>
      <text x="300" y="706" text-anchor="middle" fill="#315e4a" font-family="Arial, sans-serif" font-size="12" font-weight="700" letter-spacing="3">COMMONPLACE</text>
    </svg>`;
    return `data:image/svg+xml,${encodeURIComponent(svg)}`;
  }

  private escapeXml(value: string): string {
    return value.replace(/[<>&'"]/g, character => {
      const entities: Record<string, string> = {
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        "'": '&apos;',
        '"': '&quot;'
      };
      return entities[character];
    });
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
          cartItemId: cartItem.id,
          subtotal: Number(cartItem.subtotal),
          taxAmount: Number(cartItem.tax_amount)
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
