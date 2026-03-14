def scrape_company_posts(self, company_url, max_posts=30, days_back=7):
    """Coleta posts usando a sessão já autenticada"""
    if not self._check_login():
        print("⚠️ Sessão expirada! Faça login novamente.")
        return []
    
    print(f"\n📊 {company_url.split('/')[-2]}")
    posts_data = []
    cutoff = datetime.now() - timedelta(days=days_back)
    posts_found = 0
    
    try:
        print(f"📍 Acessando URL: {company_url}")
        self.page.goto(company_url)
        time.sleep(5)
        print(f"📍 URL atual: {self.page.url}")
        print(f"📄 Título: {self.page.title()}")
        
        # Verificar se há elementos de posts na página inicial
        posts_inicial = self.page.query_selector_all("li[data-urn], article.feed-shared-update-v2, div.occludable-update")
        print(f"🔍 Posts encontrados na página inicial: {len(posts_inicial)}")
        
        # Tentar encontrar e clicar na aba de posts
        try:
            # Procurar por links que contenham 'posts' ou 'recent-activity'
            posts_link = self.page.query_selector("a[href*='posts/']")
            if posts_link:
                print(f"✅ Link 'posts' encontrado: {posts_link.get_attribute('href')}")
                posts_link.click()
                print("✅ Aba 'posts' clicada")
            else:
                recent_link = self.page.query_selector("a[href*='recent-activity']")
                if recent_link:
                    print(f"✅ Link 'recent-activity' encontrado: {recent_link.get_attribute('href')}")
                    recent_link.click()
                    print("✅ Aba 'recent-activity' clicada")
                else:
                    print("⚠️ Nenhum link de posts encontrado. Tentando URL direta...")
                    posts_url = company_url.rstrip('/') + "/posts/?feedView=all"
                    print(f"📍 URL direta: {posts_url}")
                    self.page.goto(posts_url)
        except Exception as e:
            print(f"⚠️ Erro ao clicar na aba: {e}")
        
        time.sleep(5)
        print(f"📍 URL após navegação: {self.page.url}")
        
        # Rolar a página e coletar posts
        last_height = self.page.evaluate("document.body.scrollHeight")
        print(f"📏 Altura inicial da página: {last_height}")
        
        scroll_attempts = 0
        max_scrolls = 8
        
        while posts_found < max_posts and scroll_attempts < max_scrolls:
            # Rolar para baixo
            print(f"⬇️ Rolando página (tentativa {scroll_attempts + 1})...")
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
            
            # Coletar posts
            posts = self.page.query_selector_all("li[data-urn], article.feed-shared-update-v2, div.occludable-update")
            print(f"🔄 Total de elementos encontrados após rolagem: {len(posts)}")
            
            for i, post in enumerate(posts[posts_found:], posts_found + 1):
                try:
                    print(f"\n  --- Processando post {i} ---")
                    
                    # Extrair TODO o texto do post para diagnóstico
                    post_text = post.inner_text()
                    print(f"  📝 Texto completo do post: {post_text[:200]}...")
                    
                    # Tentar encontrar a data
                    date_text = None
                    selectores = [
                        "span.feed-shared-actor__sub-description",
                        "span.feed-shared-actor__sub-meta",
                        ".update-components-actor__sub-description",
                        ".feed-shared-actor__sub-description"
                    ]
                    
                    for selector in selectores:
                        elem = post.query_selector(selector)
                        if elem:
                            elem_text = elem.inner_text()
                            print(f"  🔍 Seletor '{selector}' retornou: '{elem_text}'")
                            
                            # Dividir por separadores
                            partes = re.split(r' • |\•|\|', elem_text)
                            print(f"  🔪 Partes divididas: {partes}")
                            
                            if len(partes) >= 2:
                                candidato = partes[1].strip()
                                print(f"  📅 Candidato (parte 2): '{candidato}'")
                                if re.search(r'\d+\s*[a-záéíóú]', candidato):
                                    date_text = candidato
                                    print(f"  ✅ Data encontrada na parte 2: '{date_text}'")
                                    break
                            
                            if not date_text:
                                for j, parte in enumerate(partes):
                                    parte_clean = parte.strip()
                                    print(f"    Parte {j}: '{parte_clean}'")
                                    if re.search(r'\d+\s*[a-záéíóú]', parte_clean):
                                        date_text = parte_clean
                                        print(f"  ✅ Data encontrada na parte {j}: '{date_text}'")
                                        break
                            if date_text:
                                break
                    
                    if not date_text:
                        print("  ⚠️ Nenhuma data encontrada neste post")
                        continue
                    
                    post_date = self._parse_date(date_text)
                    print(f"  📅 Data convertida: {post_date}")
                    
                    if not post_date:
                        print("  ⚠️ Data não reconhecida pelo parser")
                        continue
                    
                    if post_date < cutoff:
                        print(f"  ⏹️ Post antigo ({date_text}) - parando coleta")
                        return posts_data
                    
                    # Extrair conteúdo
                    content = ""
                    content_el = post.query_selector("span.break-words, div.feed-shared-inline-show-more-text span")
                    if content_el:
                        content = content_el.inner_text()[:500]
                        print(f"  📝 Conteúdo extraído: {content[:100]}...")
                    else:
                        print("  ⚠️ Conteúdo não encontrado")
                    
                    # Likes
                    likes = 0
                    likes_el = post.query_selector("span.social-details-social-counts__reactions-count")
                    if likes_el:
                        likes_text = likes_el.inner_text()
                        likes = self._extract_number(likes_text)
                        print(f"  👍 Likes: {likes} (raw: '{likes_text}')")
                    
                    # Comentários
                    comments = 0
                    comments_el = post.query_selector("li.social-details-social-counts__comments button")
                    if comments_el:
                        comments_text = comments_el.inner_text()
                        comments = self._extract_number(comments_text)
                        print(f"  💬 Comentários: {comments} (raw: '{comments_text}')")
                    
                    posts_data.append({
                        'empresa': company_url.split('/')[-2].split('?')[0],
                        'data_raw': date_text,
                        'conteudo': content,
                        'likes': likes,
                        'comentarios': comments
                    })
                    
                    posts_found += 1
                    print(f"  ✅ Post {posts_found}/{max_posts} adicionado")
                    
                    if posts_found >= max_posts:
                        break
                        
                except Exception as e:
                    print(f"  ❌ Erro ao processar post: {e}")
                    continue
            
            # Verificar fim da página
            new_height = self.page.evaluate("document.body.scrollHeight")
            print(f"📏 Altura da página: {last_height} -> {new_height}")
            if new_height == last_height:
                scroll_attempts += 1
                print(f"⏳ Fim da página alcançado (tentativa {scroll_attempts}/{max_scrolls})")
            else:
                scroll_attempts = 0
            last_height = new_height
        
        print(f"\n✅ Coleta finalizada. Total de posts encontrados: {len(posts_data)}")
        return posts_data
        
    except Exception as e:
        print(f"❌ Erro na coleta: {e}")
        import traceback
        traceback.print_exc()
        return posts_data