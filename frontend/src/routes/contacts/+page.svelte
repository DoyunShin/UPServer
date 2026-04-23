<section class="contacts">
    <div class="contacts-inner">
        <div class="contacts-header">
            <p class="contacts-label">Contacts</p>
            <h2>How you can reach us</h2>
        </div>
        <div class="contacts-grid">
            <div class="contact-card">
                <div class="contact-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z"/>
                    </svg>
                </div>
                <div class="contact-text">
                    <h3>Phone</h3>
                    <p>+123456789</p>
                </div>
            </div>
            <div class="contact-card">
                <div class="contact-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"/>
                    </svg>
                </div>
                <div class="contact-text">
                    <h3>Email</h3>
                    <p>info@example.com</p>
                </div>
            </div>
            <div class="contact-card">
                <div class="contact-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z"/>
                    </svg>
                </div>
                <div class="contact-text">
                    <h3>Location</h3>
                    <p>12 Example Street</p>
                </div>
            </div>
        </div>
    </div>
</section>

<style>
    .contacts {
        padding: 3rem 1.5rem;
    }
    .contacts-inner {
        max-width: 720px;
        margin: 0 auto;
    }
    .contacts-header {
        text-align: center;
        margin-bottom: 3rem;
    }
    .contacts-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--color-accent);
        margin: 0 0 0.75rem;
    }
    .contacts-header h2 {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.01em;
    }
    .contacts-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }
    .contact-card {
        background-color: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        transition: all var(--transition);
    }
    .contact-card:hover {
        background-color: var(--color-surface-hover);
        border-color: rgba(255, 255, 255, 0.1);
    }
    .contact-icon {
        color: var(--color-accent);
        flex-shrink: 0;
        margin-top: 2px;
    }
    .contact-text h3 {
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0 0 0.25rem;
    }
    .contact-text p {
        font-size: 0.8rem;
        color: var(--color-text-muted);
        margin: 0;
    }
</style>
