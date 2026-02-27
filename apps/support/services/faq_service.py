from ..models import FAQArticle, FAQCategory


class FAQService:
    @staticmethod
    def get_relevant_articles(query, category=None, limit=5):
        queryset = FAQArticle.objects.filter(is_active=True)

        if category:
            queryset = queryset.filter(category__slug=category)

        # Simple search by keywords
        if query:
            keywords = query.lower().split()
            for keyword in keywords:
                queryset = queryset.filter(keywords__icontains=keyword)

        return queryset[:limit]

    @staticmethod
    def increment_views(article):
        article.views_count += 1
        article.save(update_fields=['views_count'])

    @staticmethod
    def vote_helpful(article, helpful):
        if helpful:
            article.helpful_yes += 1
        else:
            article.helpful_no += 1
        article.save(update_fields=['helpful_yes', 'helpful_no'])
