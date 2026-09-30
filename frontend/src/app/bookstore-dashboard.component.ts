import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from './auth.service';

interface Book {
  id: number;
  title: string;
  author: string;
  category: string;
  catalog: string;
  itemCode: string;
  price: number;
  isbn: string;
  badge?: string;
}

interface BookDraft {
  title: string;
  author: string;
  category: string;
  catalog: string;
  itemCode: string;
  price: number;
  isbn: string;
  badge: string;
}

interface BagItem {
  book: Book;
  quantity: number;
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
  private readonly router = inject(Router);

  readonly signedInRole = this.authService.currentRole ?? 'Student';
  readonly isManager = this.signedInRole === 'Manager';
  readonly isStudent = this.signedInRole === 'Student';
  readonly categories = ['All books', 'Fiction', 'Mystery', 'Fantasy', 'Non-fiction'];
  catalogs = ['New & noteworthy', 'Fiction shelf', 'Mystery shelf', 'Fantasy shelf', 'Non-fiction shelf'];
  books: Book[] = [
    { id: 1, title: 'The Midnight Library', author: 'Matt Haig', category: 'Fiction', catalog: 'New & noteworthy', itemCode: 'BK-0001', price: 18.00, isbn: '9780525559474', badge: 'Book club pick' },
    { id: 2, title: 'The Thursday Murder Club', author: 'Richard Osman', category: 'Mystery', catalog: 'Mystery shelf', itemCode: 'BK-0002', price: 17.50, isbn: '9781984880987', badge: 'Bestseller' },
    { id: 3, title: 'A Psalm for the Wild-Built', author: 'Becky Chambers', category: 'Fantasy', catalog: 'Fantasy shelf', itemCode: 'BK-0003', price: 16.00, isbn: '9781250236210', badge: 'Staff pick' },
    { id: 4, title: 'Braiding Sweetgrass', author: 'Robin Wall Kimmerer', category: 'Non-fiction', catalog: 'Non-fiction shelf', itemCode: 'BK-0004', price: 19.00, isbn: '9781571313560' },
    { id: 5, title: 'The Very Secret Society of Irregular Witches', author: 'Sangu Mandanna', category: 'Fantasy', catalog: 'Fantasy shelf', itemCode: 'BK-0005', price: 18.00, isbn: '9780593439358' },
    { id: 6, title: 'The Creative Act', author: 'Rick Rubin', category: 'Non-fiction', catalog: 'New & noteworthy', itemCode: 'BK-0006', price: 24.00, isbn: '9780593652886', badge: 'A shop favorite' },
    { id: 7, title: 'The Song of Achilles', author: 'Madeline Miller', category: 'Fiction', catalog: 'Fiction shelf', itemCode: 'BK-0007', price: 17.00, isbn: '9780062060624' },
    { id: 8, title: 'The House in the Cerulean Sea', author: 'TJ Klune', category: 'Fiction', catalog: 'Fiction shelf', itemCode: 'BK-0008', price: 18.00, isbn: '9781250217288' }
  ];

  searchTerm = '';
  itemCodeQuery = '';
  itemCodeMessage = '';
  itemCodeSuggestionSelected = false;
  activeItemCodeIndex = -1;
  selectedCategory = 'All books';
  selectedCatalog = 'All catalogs';
  newCatalogName = '';
  showBookEditor = false;
  editingBookId: number | null = null;
  bookDraft: BookDraft = this.createBookDraft();
  bag: BagItem[] = [];
  bagMessage = '';
  checkoutMessage = '';
  showBag = false;
  paymentMethod: 'cash' | 'card' = 'cash';
  cashReceived: number | null = null;
  receipt: SaleReceipt | null = null;
  showReceipt = false;
  editorError = '';

  constructor() {
    this.restoreCatalog();
  }

  get filteredBooks(): Book[] {
    const query = this.searchTerm.trim().toLowerCase();

    return this.books.filter(book => {
      const matchesCategory = this.selectedCategory === 'All books' || book.category === this.selectedCategory;
      const matchesCatalog = this.selectedCatalog === 'All catalogs' || book.catalog === this.selectedCatalog;
      const matchesSearch = !query || `${book.title} ${book.author} ${book.category} ${book.catalog}`.toLowerCase().includes(query);
      return matchesCategory && matchesCatalog && matchesSearch;
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
    this.itemCodeMessage = `${book.title} added to your cart.`;
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

    const existingItem = this.bag.find(item => item.book.id === book.id);

    if (existingItem) {
      existingItem.quantity += 1;
    } else {
      this.bag.push({ book, quantity: 1 });
    }

    this.bagMessage = `${book.title} added to your bag.`;
    this.checkoutMessage = '';
  }

  changeQuantity(item: BagItem, change: number): void {
    item.quantity += change;

    if (item.quantity < 1) {
      this.bag = this.bag.filter(bagItem => bagItem !== item);
    }

    this.checkoutMessage = '';
  }

  removeFromBag(item: BagItem): void {
    this.bag = this.bag.filter(bagItem => bagItem !== item);
    this.checkoutMessage = '';
  }

  checkout(): void {
    this.checkoutMessage = 'Checkout is not connected yet. Your bag is saved while you browse.';
  }

  completeStudentSale(): void {
    if (!this.canCompleteStudentSale) {
      return;
    }

    const total = this.bagTotal;
    const received = Number(this.cashReceived ?? 0);
    this.receipt = {
      number: `CP-${Date.now().toString().slice(-6)}`,
      issuedAt: new Date().toLocaleString(),
      items: this.bag.map(item => ({
        title: item.book.title,
        itemCode: item.book.itemCode,
        quantity: item.quantity,
        unitPrice: item.book.price,
        lineTotal: item.book.price * item.quantity
      })),
      total,
      paymentMethod: this.paymentMethod,
      ...(this.paymentMethod === 'cash' ? { cashReceived: received, changeDue: received - total } : {})
    };

    this.bag = [];
    this.cashReceived = null;
    this.paymentMethod = 'cash';
    this.showBag = false;
    this.showReceipt = true;
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
    this.bookDraft = book ? { ...book, badge: book.badge ?? '' } : this.createBookDraft();
    this.editorError = '';
    this.showBookEditor = true;
  }

  saveBook(): void {
    if (!this.isManager || !this.bookDraft.title.trim() || !this.bookDraft.author.trim() || !this.bookDraft.isbn.trim() || !this.bookDraft.itemCode.trim()) {
      return;
    }

    const itemCode = this.bookDraft.itemCode.trim().toUpperCase();
    const duplicateCode = this.books.some(item => item.itemCode.toUpperCase() === itemCode && item.id !== this.editingBookId);
    if (duplicateCode) {
      this.editorError = 'That item code is already in use.';
      return;
    }

    const book: Book = {
      ...this.bookDraft,
      id: this.editingBookId ?? Math.max(0, ...this.books.map(item => item.id)) + 1,
      title: this.bookDraft.title.trim(),
      author: this.bookDraft.author.trim(),
      itemCode,
      isbn: this.bookDraft.isbn.trim(),
      badge: this.bookDraft.badge.trim() || undefined,
      price: Number(this.bookDraft.price)
    };

    if (this.editingBookId === null) {
      this.books = [book, ...this.books];
    } else {
      this.books = this.books.map(item => item.id === book.id ? book : item);
      this.bag = this.bag.map(item => item.book.id === book.id ? { ...item, book } : item);
    }

    this.persistCatalog();
    this.closeBookEditor();
  }

  removeBook(book: Book): void {
    if (!this.isManager) {
      return;
    }

    this.books = this.books.filter(item => item.id !== book.id);
    this.bag = this.bag.filter(item => item.book.id !== book.id);
    this.persistCatalog();
  }

  addCatalog(): void {
    if (!this.isManager) {
      return;
    }

    const name = this.newCatalogName.trim();
    if (!name || this.catalogs.some(catalog => catalog.toLowerCase() === name.toLowerCase())) {
      return;
    }

    this.catalogs = [...this.catalogs, name];
    this.newCatalogName = '';
    this.selectedCatalog = name;
    this.persistCatalog();
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
    const nextId = Math.max(0, ...this.books.map(book => book.id)) + 1;
    return {
      title: '',
      author: '',
      category: 'Fiction',
      catalog: this.catalogs?.[0] ?? 'New & noteworthy',
      itemCode: `BK-${String(nextId).padStart(4, '0')}`,
      price: 18,
      isbn: '',
      badge: ''
    };
  }

  private restoreCatalog(): void {
    try {
      const savedCatalog = localStorage.getItem('commonplace-store-catalog');
      if (!savedCatalog) {
        return;
      }

      const parsed = JSON.parse(savedCatalog) as { books?: Array<Book & { itemCode?: string }>; catalogs?: string[] };
      if (Array.isArray(parsed.books) && Array.isArray(parsed.catalogs)) {
        this.books = parsed.books.map((book, index) => ({
          ...book,
          itemCode: book.itemCode?.trim() || `BK-${String(book.id ?? index + 1).padStart(4, '0')}`
        }));
        this.catalogs = parsed.catalogs;
      }
    } catch {
      localStorage.removeItem('commonplace-store-catalog');
    }
  }

  private persistCatalog(): void {
    try {
      localStorage.setItem('commonplace-store-catalog', JSON.stringify({ books: this.books, catalogs: this.catalogs }));
    } catch {
      return;
    }
  }
}
